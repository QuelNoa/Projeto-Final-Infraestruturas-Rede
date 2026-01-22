#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime


def fmt(v):
    return "-" if v is None else str(v)


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python3 scripts/write_metrics_md.py <RUN_DIR>", file=sys.stderr)
        return 2

    run_dir = Path(sys.argv[1]).resolve()
    mpath = run_dir / "metrics.json"
    if not mpath.exists():
        print(f"Erro: falta {mpath} (corre calc_resilience_metrics.py primeiro)", file=sys.stderr)
        return 2

    data = json.loads(mpath.read_text(encoding="utf-8"))

    stable_n = data.get("stable_n")
    post_window = data.get("post_window_s")
    rpo = data.get("rpo")

    overlaps = data.get("overlaps", [])
    incidents = data.get("incidents", {})
    k6 = data.get("k6", {})

    lines = []
    lines.append(f"# Métricas de Resiliência — {run_dir.name}")
    lines.append("")
    lines.append(f"- Diretoria do run: `{data.get('run_dir')}`")
    lines.append(f"- Recuperação estável: **{stable_n} OK consecutivos**")
    lines.append(f"- Janela pós-incidente: **{post_window}s**")
    lines.append(f"- RPO: **{rpo}**")
    lines.append("")

    baseline = data.get("baseline", {})
    lines.append("## Baseline")
    lines.append(f"- FIRST_FAILURE antes do 1º incidente: **{baseline.get('first_failure_at') or '—'}**")
    lines.append(f"- Nota: {baseline.get('note','')}")
    lines.append("")

    lines.append("## Incidentes (MTTD / MTTR / RTO)")
    if not incidents:
        lines.append("_Sem incidentes encontrados._")
    else:
        for itype, per_ep in incidents.items():
            lines.append(f"### {itype}")
            for ep, vals in per_ep.items():
                lines.append(f"- **{ep}**")
                lines.append(f"  - Início: {vals.get('t_incident_start')}")
                lines.append(f"  - Fim: {vals.get('t_incident_end')}")
                lines.append(f"  - FIRST_FAILURE: {vals.get('t_first_failure') or '—'}")
                lines.append(f"  - RECOVERED (estável): {vals.get('t_recovered_stable') or '—'}")
                lines.append(f"  - MTTD(s): {fmt(vals.get('mttd_s'))}")
                lines.append(f"  - MTTR(s): {fmt(vals.get('mttr_s'))}")
                lines.append(f"  - RTO(s): {fmt(vals.get('rto_s'))}")
                note = vals.get("note")
                if note:
                    lines.append(f"  - Nota: {note}")
            lines.append("")

    if overlaps:
        lines.append("## Avisos de sobreposição")
        for o in overlaps:
            lines.append(f"- {o['a']} ↔ {o['b']} ({o['a_start']}..{o['a_end']} | {o['b_start']}..{o['b_end']})")
            lines.append(f"  - {o.get('note','')}")
        lines.append("")

    lines.append("## DoS (k6)")
    lines.append(f"- http_reqs: **{k6.get('http_reqs') or '—'}**")
    lines.append(f"- p95: **{k6.get('http_req_duration_p95_ms') or '—'} ms**")
    lines.append(f"- max: **{k6.get('http_req_duration_max_ms') or '—'} ms**")
    if k6.get("source"):
        lines.append(f"- fonte: `{k6.get('source')}`")
    lines.append("")

    out_path = run_dir / "metrics.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] metrics.md criado: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
