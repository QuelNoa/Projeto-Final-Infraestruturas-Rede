#!/usr/bin/env python3
from __future__ import annotations
import csv, json, re, sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

TS_RE = re.compile(r"^\[(?P<ts>[^]]+)\]\s+(?P<msg>.*)$")
INC_START_RE = re.compile(r"INCIDENT_START type=(?P<typ>\S+)")
INC_END_RE   = re.compile(r"INCIDENT_END type=(?P<typ>\S+)")
FIRST_RE     = re.compile(r"FIRST_FAILURE ping_ok=(?P<p>\d) secure_ok=(?P<s>\d)")
RECOV_RE     = re.compile(r"RECOVERED ping_ok=(?P<p>\d) secure_ok=(?P<s>\d)")
ACTION_DEL_RE= re.compile(r"ACTION deleting_one_api_pod")

def parse_ts(s: str) -> datetime:
    # aceita date -Is e -Iseconds (com timezone)
    # Ex: 2026-01-21T03:43:58+00:00
    return datetime.fromisoformat(s).astimezone(timezone.utc)

@dataclass
class Incident:
    typ: str
    start: datetime | None = None
    end: datetime | None = None
    action_t0: datetime | None = None  # p/ RTO kill_api

def load_events(events_path: Path):
    lines = events_path.read_text(encoding="utf-8", errors="replace").splitlines()
    parsed = []
    for ln in lines:
        m = TS_RE.match(ln.strip())
        if not m: 
            continue
        ts = parse_ts(m.group("ts"))
        msg = m.group("msg")
        parsed.append((ts, msg))
    return parsed

def load_http(csv_path: Path):
    rows = []
    with csv_path.open(newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            # ts_iso,endpoint,http_code,lat_ms,ok
            ts = parse_ts(row["ts_iso"])
            endpoint = row["endpoint"]
            ok = int(row["ok"])
            code = row["http_code"]
            rows.append((ts, endpoint, ok, code))
    return rows

def first_degrade_after(http_rows, t0: datetime, endpoints: set[str]):
    for ts, ep, ok, code in http_rows:
        if ts >= t0 and ep in endpoints and ok == 0:
            return ts
    return None

def recovered_stable_after(http_rows, t_start: datetime, endpoint: str, stable_n: int = 3):
    # primeiro instante em que há stable_n amostras consecutivas ok==1 para endpoint
    consec = 0
    first_ts = None
    for ts, ep, ok, code in http_rows:
        if ts < t_start or ep != endpoint:
            continue
        if ok == 1:
            consec += 1
            if consec == 1:
                first_ts = ts
            if consec >= stable_n:
                return first_ts
        else:
            consec = 0
            first_ts = None
    return None

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 scripts/make_metrics.py <RUN_DIR>", file=sys.stderr)
        sys.exit(2)

    run_dir = Path(sys.argv[1])
    events_path = run_dir / "events.log"
    http_path = run_dir / "http_metrics.csv"

    if not events_path.exists():
        raise SystemExit(f"Falta {events_path}")
    if not http_path.exists():
        raise SystemExit(f"Falta {http_path}")

    ev = load_events(events_path)
    http = load_http(http_path)

    # recolhe incidentes
    incidents: dict[str, Incident] = {}
    first_failure: datetime | None = None
    recovered: datetime | None = None

    for ts, msg in ev:
        m = INC_START_RE.search(msg)
        if m:
            typ = m.group("typ")
            incidents.setdefault(typ, Incident(typ=typ)).start = ts
            continue
        m = INC_END_RE.search(msg)
        if m:
            typ = m.group("typ")
            incidents.setdefault(typ, Incident(typ=typ)).end = ts
            continue
        if ACTION_DEL_RE.search(msg):
            # isto acontece dentro do kill_api
            inc = incidents.setdefault("kill_api", Incident(typ="kill_api"))
            inc.action_t0 = ts
            continue
        m = FIRST_RE.search(msg)
        if m and first_failure is None:
            first_failure = ts
            continue
        m = RECOV_RE.search(msg)
        if m:
            recovered = ts  # fica o último RECOVERED global; ok

    # calcula métricas por incidente usando o http_metrics como fonte “de verdade”
    stable_n = 3
    out = {
        "run_dir": str(run_dir),
        "rpo": "0 (stateless/NA)",
        "stable_n": stable_n,
        "incidents": {}
    }

    for typ, inc in sorted(incidents.items()):
        if not inc.start:
            continue

        # MTTD: INCIDENT_START -> primeira degradação observada (ok==0) após start
        # preferimos degradar em /secure-data (é o mais sensível) mas aceitamos /ping
        t_detect = first_degrade_after(http, inc.start, {"/secure-data", "/ping"})
        mttd_s = (t_detect - inc.start).total_seconds() if t_detect else None

        # MTTR: t_detect -> recovered (estável)
        # fazemos duas leituras: recovery de serviço (/ping) e recovery funcional (/secure-data)
        rec_ping = recovered_stable_after(http, t_detect or inc.start, "/ping", stable_n=stable_n)
        rec_secure = recovered_stable_after(http, t_detect or inc.start, "/secure-data", stable_n=stable_n)

        mttr_ping_s = (rec_ping - t_detect).total_seconds() if (t_detect and rec_ping) else None
        mttr_secure_s = (rec_secure - t_detect).total_seconds() if (t_detect and rec_secure) else None

        entry = {
            "t_start_utc": inc.start.isoformat(),
            "t_end_utc": inc.end.isoformat() if inc.end else None,
            "t_detect_utc": t_detect.isoformat() if t_detect else None,
            "recovered_ping_utc": rec_ping.isoformat() if rec_ping else None,
            "recovered_secure_utc": rec_secure.isoformat() if rec_secure else None,
            "mttd_s": mttd_s,
            "mttr_s_service_ping": mttr_ping_s,
            "mttr_s_functional_secure": mttr_secure_s,
        }

        # RTO: só faz sentido no kill_api (t0 = ACTION deleting_one_api_pod)
        if typ == "kill_api" and inc.action_t0:
            rto_ping = recovered_stable_after(http, inc.action_t0, "/ping", stable_n=stable_n)
            rto_secure = recovered_stable_after(http, inc.action_t0, "/secure-data", stable_n=stable_n)
            entry["t0_action_utc"] = inc.action_t0.isoformat()
            entry["rto_s_service_ping"] = (rto_ping - inc.action_t0).total_seconds() if rto_ping else None
            entry["rto_s_functional_secure"] = (rto_secure - inc.action_t0).total_seconds() if rto_secure else None

        out["incidents"][typ] = entry

    # escreve metrics.json
    (run_dir / "metrics.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    # escreve metrics.md 
    def fmt(x):
        return "n/a" if x is None else f"{x:.1f}s"

    lines = []
    lines.append(f"# Métricas de resiliência ({run_dir.name})\n")
    lines.append(f"- RPO: {out['rpo']}")
    lines.append(f"- Critério de estabilidade: {stable_n} amostras consecutivas OK\n")
    lines.append("| Incidente | MTTD | MTTR (serviço /ping) | MTTR (funcional /secure-data) | RTO (serviço) | RTO (funcional) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for typ, e in out["incidents"].items():
        lines.append("| " + typ
            + " | " + fmt(e.get("mttd_s"))
            + " | " + fmt(e.get("mttr_s_service_ping"))
            + " | " + fmt(e.get("mttr_s_functional_secure"))
            + " | " + fmt(e.get("rto_s_service_ping"))
            + " | " + fmt(e.get("rto_s_functional_secure"))
            + " |")
    (run_dir / "metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
