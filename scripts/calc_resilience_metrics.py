#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Tuple


ISO_RE = re.compile(r"^\[(?P<ts>[^]]+)\]\s+(?P<msg>.*)$")


def parse_ts(s: str) -> datetime:
    # ex: 2026-01-21T05:55:44+00:00
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def fmt_ts(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


@dataclass
class Incident:
    type: str
    start: datetime
    end: datetime
    raw_lines: List[str]


@dataclass
class Point:
    ts: datetime
    endpoint: str
    http_code: int
    ok: int  # 1/0


def load_http_metrics(csv_path: Path) -> List[Point]:
    pts: List[Point] = []
    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ts = parse_ts(row["ts_iso"])
            endpoint = row["endpoint"]
            code_str = row["http_code"].strip()
            try:
                code = int(code_str)
            except Exception:
                code = 0
            ok = int(row["ok"])
            pts.append(Point(ts=ts, endpoint=endpoint, http_code=code, ok=ok))
    pts.sort(key=lambda p: p.ts)
    return pts


def load_monitor_events(events_log: Path) -> List[Tuple[datetime, str]]:
    out: List[Tuple[datetime, str]] = []
    if not events_log.exists():
        return out
    for line in events_log.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ISO_RE.match(line.strip())
        if not m:
            continue
        ts = parse_ts(m.group("ts"))
        msg = m.group("msg")
        out.append((ts, msg))
    out.sort(key=lambda x: x[0])
    return out


def load_incidents(run_dir: Path) -> Dict[str, Incident]:
    incidents: Dict[str, Incident] = {}
    # cada incidente tem pasta <type>/events.log gerado por run_incident.sh
    for inc_type in ["dos", "kill_api", "netfail"]:
        p = run_dir / inc_type / "events.log"
        if not p.exists():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        t_start = None
        t_end = None
        for line in lines:
            m = ISO_RE.match(line.strip())
            if not m:
                continue
            ts = parse_ts(m.group("ts"))
            msg = m.group("msg")
            if "INCIDENT_START" in msg:
                t_start = ts
            if "INCIDENT_END" in msg:
                t_end = ts
        if t_start and t_end:
            incidents[inc_type] = Incident(type=inc_type, start=t_start, end=t_end, raw_lines=lines)
    return incidents


def overlaps(a: Incident, b: Incident) -> bool:
    return not (a.end <= b.start or b.end <= a.start)


def first_failure_in_window(
    pts: List[Point],
    endpoint: str,
    t0: datetime,
    t1: datetime
) -> Optional[datetime]:
    for p in pts:
        if p.endpoint != endpoint:
            continue
        if p.ts < t0:
            continue
        if p.ts > t1:
            break
        if p.ok == 0:
            return p.ts
    return None


def stable_recovery_time(
    pts: List[Point],
    endpoint: str,
    t_from: datetime,
    t_until: datetime,
    stable_n: int
) -> Optional[datetime]:
    # “recuperação estável”: stable_n OK consecutivos
    streak = 0
    candidate_ts: Optional[datetime] = None
    for p in pts:
        if p.endpoint != endpoint:
            continue
        if p.ts < t_from:
            continue
        if p.ts > t_until:
            break
        if p.ok == 1:
            if streak == 0:
                candidate_ts = p.ts
            streak += 1
            if streak >= stable_n:
                return candidate_ts
        else:
            streak = 0
            candidate_ts = None
    return None


def parse_k6_summary(k6_path: Path) -> Dict[str, Optional[float]]:
    if not k6_path.exists():
        return {"http_reqs": None, "p95_ms": None, "max_ms": None}
    try:
        data = json.loads(k6_path.read_text(encoding="utf-8"))
    except Exception:
        return {"http_reqs": None, "p95_ms": None, "max_ms": None}

    m = data.get("metrics", {})

    # suportar estruturas diferentes:
    # - m["http_reqs"] = {"count":..., "rate":...}
    # - ou m["http_reqs"]["values"]["count"] etc (se existir noutro formato)
    def get_count(metric_name: str) -> Optional[float]:
        mm = m.get(metric_name)
        if not isinstance(mm, dict):
            return None
        if "count" in mm and isinstance(mm["count"], (int, float)):
            return float(mm["count"])
        vv = mm.get("values")
        if isinstance(vv, dict) and "count" in vv and isinstance(vv["count"], (int, float)):
            return float(vv["count"])
        return None

    def get_duration_p95_max(metric_name: str) -> Tuple[Optional[float], Optional[float]]:
        mm = m.get(metric_name)
        if not isinstance(mm, dict):
            return (None, None)
        # no teu ficheiro: "p(95)" e "max" estão ao nível de topo
        p95 = mm.get("p(95)")
        mx = mm.get("max")
        if isinstance(p95, (int, float)) and isinstance(mx, (int, float)):
            return (float(p95), float(mx))
        # fallback para formatos alternativos
        vv = mm.get("values")
        if isinstance(vv, dict):
            p95b = vv.get("p(95)") or vv.get("p95")
            mxb = vv.get("max")
            p95_ok = float(p95b) if isinstance(p95b, (int, float)) else None
            mx_ok = float(mxb) if isinstance(mxb, (int, float)) else None
            return (p95_ok, mx_ok)
        return (None, None)

    http_reqs = get_count("http_reqs")
    p95, mx = get_duration_p95_max("http_req_duration")

    return {"http_reqs": http_reqs, "p95_ms": p95, "max_ms": mx}


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python3 scripts/calc_resilience_metrics.py <RUN_DIR>", file=sys.stderr)
        return 2

    run_dir = Path(sys.argv[1]).resolve()
    http_csv = run_dir / "http_metrics.csv"
    monitor_events_log = run_dir / "events.log"

    if not http_csv.exists():
        print(f"Erro: falta {http_csv}", file=sys.stderr)
        return 2

    pts = load_http_metrics(http_csv)
    incidents = load_incidents(run_dir)

    # ordena incidentes por start
    inc_list = sorted(incidents.values(), key=lambda i: i.start)

    # baseline: FIRST_FAILURE só conta se for ANTES do primeiro incidente
    monitor_events = load_monitor_events(monitor_events_log)
    first_inc_start = inc_list[0].start if inc_list else None

    baseline_first_failure = None
    if first_inc_start:
        for ts, msg in monitor_events:
            if "FIRST_FAILURE" in msg and ts < first_inc_start:
                baseline_first_failure = ts
                break

    stable_n = int((run_dir / "stable_n.txt").read_text().strip()) if (run_dir / "stable_n.txt").exists() else 3
    post_window_s = int((run_dir / "post_window_s.txt").read_text().strip()) if (run_dir / "post_window_s.txt").exists() else 30

    endpoints = ["/ping", "/secure-data"]

    out: Dict[str, object] = {
        "run_dir": str(run_dir),
        "rpo": "0 (stateless/NA)",
        "stable_n": stable_n,
        "post_window_s": post_window_s,
        "baseline": {
            "first_failure_at": fmt_ts(baseline_first_failure),
            "note": "Baseline FIRST_FAILURE só é considerado se ocorrer antes do 1º INCIDENT_START."
        },
        "incidents": {},
        "overlaps": [],
    }

    # overlaps (informação explícita para o relatório)
    for i in range(len(inc_list)):
        for j in range(i + 1, len(inc_list)):
            a, b = inc_list[i], inc_list[j]
            if overlaps(a, b):
                out["overlaps"].append({
                    "a": a.type, "b": b.type,
                    "a_start": fmt_ts(a.start), "a_end": fmt_ts(a.end),
                    "b_start": fmt_ts(b.start), "b_end": fmt_ts(b.end),
                    "note": "Incidentes sobrepostos podem contaminar atribuição causal de falhas."
                })

    for inc in inc_list:
        win_end = inc.end + timedelta(seconds=post_window_s)

        inc_obj: Dict[str, object] = {}
        for ep in endpoints:
            t_first = first_failure_in_window(pts, ep, inc.start, win_end)
            t_recovered = None
            if t_first:
                t_recovered = stable_recovery_time(pts, ep, t_first, win_end, stable_n)

            mttd = (t_first - inc.start).total_seconds() if t_first else None
            mttr = (t_recovered - t_first).total_seconds() if (t_first and t_recovered) else None

            # RTO: no teu enunciado tu queres "kill_api até recuperar /ping"
            # mas mantemos cálculo genérico: se houver falha, RTO pode ser do start até recover.
            rto = (t_recovered - inc.start).total_seconds() if (t_recovered and t_first) else None

            inc_obj[ep] = {
                "t_incident_start": fmt_ts(inc.start),
                "t_incident_end": fmt_ts(inc.end),
                "window_end": fmt_ts(win_end),
                "t_first_failure": fmt_ts(t_first),
                "t_recovered_stable": fmt_ts(t_recovered),
                "mttd_s": mttd,
                "mttr_s": mttr,
                "rto_s": rto,
                "note": (
                    "Sem falha detetada na janela do incidente."
                    if not t_first else
                    ("Falha detetada, mas sem recuperação estável na janela." if (t_first and not t_recovered) else None)
                )
            }

        out["incidents"][inc.type] = inc_obj

    # k6
    k6_path = run_dir / "dos" / "k6_summary.json"
    k6 = parse_k6_summary(k6_path)
    out["k6"] = {
        "http_reqs": k6["http_reqs"],
        "http_req_duration_p95_ms": k6["p95_ms"],
        "http_req_duration_max_ms": k6["max_ms"],
        "source": str(k6_path) if k6_path.exists() else None,
    }

    metrics_path = run_dir / "metrics.json"
    metrics_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] metrics.json criado: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
