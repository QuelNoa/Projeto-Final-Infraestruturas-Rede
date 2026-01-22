#!/usr/bin/env python3
import math
import os
import sys
from datetime import datetime
from collections import defaultdict

import matplotlib.pyplot as plt

def parse_metrics_tsv(path: str):
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # detetar delimitador
            if "\t" in line:
                parts = line.split("\t")
            elif ";" in line:
                parts = line.split(";")
            elif "," in line:
                parts = line.split(",")
            else:
                parts = line.split()  # whitespace

            # tolerância a colunas extra (ficamos com as 5 primeiras)
            if len(parts) < 5:
                continue
            parts = parts[:5]

            ts, ep, status, lat, ok = [p.strip() for p in parts]

            # ignorar cabeçalhos/linhas não ISO
            if not ts.startswith("20") or "T" not in ts:
                continue

            try:
                dt = datetime.fromisoformat(ts)
            except:
                continue

            try:
                status_i = int(float(status))
            except:
                status_i = 0

            try:
                lat_i = int(float(lat))
            except:
                lat_i = 0

            ok_s = ok.strip().lower()
            ok_i = 1 if ok_s in ("1", "true", "ok") else 0

            rows.append((dt, ep, status_i, lat_i, ok_i))
    return rows


def p95(vals):
    if not vals:
        return 0
    vals = sorted(vals)
    k = int(math.ceil(0.95 * len(vals))) - 1
    k = max(0, min(k, len(vals)-1))
    return vals[k]

def merge_events(run_dir: str):
    lines = []
    # raiz
    root = os.path.join(run_dir, "events.log")
    if os.path.isfile(root):
        lines += open(root, "r", encoding="utf-8", errors="ignore").read().splitlines()

    # subpastas (2 níveis)
    for sub in ("dos", "kill", "netfail"):
        p = os.path.join(run_dir, sub, "events.log")
        if os.path.isfile(p):
            lines += open(p, "r", encoding="utf-8", errors="ignore").read().splitlines()

    # fallback: procurar events.log em subpastas, se existirem mais
    for dirpath, dirnames, filenames in os.walk(run_dir):
        if dirpath == run_dir:
            continue
        if "events.log" in filenames:
            p = os.path.join(dirpath, "events.log")
            if p not in (root,):
                lines += open(p, "r", encoding="utf-8", errors="ignore").read().splitlines()

    # ordenar lexicograficamente por timestamp ISO (funciona)
    lines = sorted(set(lines))
    return lines

def parse_incident_windows(event_lines):
    # devolve lista de (type, start_dt, end_dt)
    starts = {}
    ends = {}
    for line in event_lines:
        if not line.startswith("["):
            continue
        try:
            ts = line.split("]",1)[0].strip("[]")
            dt = datetime.fromisoformat(ts)
        except:
            continue
        msg = line.split("]",1)[1].strip()

        if "INCIDENT_START" in msg and "type=" in msg:
            t = msg.split("type=",1)[1].split()[0]
            starts.setdefault(t, dt)
        if "INCIDENT_END" in msg and "type=" in msg:
            t = msg.split("type=",1)[1].split()[0]
            ends[t] = dt

    windows = []
    for t, sdt in starts.items():
        edt = ends.get(t)
        windows.append((t, sdt, edt))
    return windows

def main():
    if len(sys.argv) != 2:
        print("Uso: python3 scripts/make_report.py <results/run_dir>")
        sys.exit(1)

    run_dir = sys.argv[1]
    metrics_path = os.path.join(run_dir, "http_metrics.csv")
    if not os.path.isfile(metrics_path):
        print(f"Ficheiro não encontrado: {metrics_path}")
        sys.exit(1)

    rows = parse_metrics_tsv(metrics_path)
    per = defaultdict(lambda: {"count":0,"ok":0,"max":0,"lats":[]})

    first_failure = None
    for dt, ep, status, lat, ok in rows:
        s = per[ep]
        s["count"] += 1
        s["ok"] += ok
        s["max"] = max(s["max"], lat)
        s["lats"].append(lat)
        if first_failure is None and ok == 0:
            first_failure = (dt, ep, status, lat)

    table = []
    for ep in sorted(per.keys()):
        s = per[ep]
        okp = (s["ok"]/s["count"]*100.0) if s["count"] else 0.0
        p95v = p95(s["lats"])
        table.append((ep, s["count"], okp, s["max"], p95v))

    # --- gráficos ---
    out_dir = run_dir
    fig1 = os.path.join(out_dir, "ok_rate.png")
    fig2 = os.path.join(out_dir, "latency.png")
    fig3 = os.path.join(out_dir, "timeline.png")

    endpoints = [r[0] for r in table]
    ok_rates = [r[2] for r in table]
    max_lats = [r[3] for r in table]
    p95_lats = [r[4] for r in table]

    # ok% por endpoint
    plt.figure()
    plt.bar(endpoints, ok_rates)
    plt.ylabel("OK (%)")
    plt.title("OK% por endpoint")
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(fig1, dpi=160)
    plt.close()

    # latência (p95 e max)
    plt.figure()
    x = range(len(endpoints))
    plt.bar([i-0.2 for i in x], p95_lats, width=0.4, label="p95 (ms)")
    plt.bar([i+0.2 for i in x], max_lats, width=0.4, label="max (ms)")
    plt.xticks(list(x), endpoints)
    plt.ylabel("Latência (ms)")
    plt.title("Latência por endpoint")
    plt.legend()
    plt.tight_layout()
    plt.savefig(fig2, dpi=160)
    plt.close()

    # timeline simples (incidentes)
    events = merge_events(run_dir)
    windows = parse_incident_windows(events)

    # timeline usa intervalo das métricas
    t0 = rows[0][0] if rows else None
    t1 = rows[-1][0] if rows else None

    plt.figure()
    if t0 and t1:
        plt.plot([t0, t1], [0, 0])  # linha base invisível
        y = 1
        for t, sdt, edt in windows:
            if edt is None:
                edt = t1
            plt.hlines(y, sdt, edt, linewidth=6)
            plt.text(sdt, y+0.1, t, fontsize=9)
            y += 1
        if first_failure:
            dt, ep, status, lat = first_failure
            plt.vlines(dt, 0, max(1,y), linestyles="dashed")
            plt.text(dt, 0.2, f"FIRST_FAILURE ({ep} {status})", rotation=90, fontsize=8)
        plt.yticks([])
        plt.title("Timeline (incidentes + first failure)")
        plt.tight_layout()
        plt.savefig(fig3, dpi=160)
    plt.close()

    # --- HTML ---
    report_path = os.path.join(out_dir, "report.html")
    def esc(s): return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

    ff_line = "n/a"
    if first_failure:
        dt, ep, status, lat = first_failure
        ff_line = f"{dt.isoformat()} endpoint={ep} status={status} lat_ms={lat}"

    rows_html = "\n".join(
        f"<tr><td>{esc(ep)}</td><td>{cnt}</td><td>{okp:.1f}</td><td>{mx}</td><td>{p95v}</td></tr>"
        for ep, cnt, okp, mx, p95v in table
    )

    events_html = "<br>".join(esc(l) for l in events if any(k in l for k in ("INCIDENT_START","INCIDENT_END","FIRST_FAILURE","FIRST_SUCCESS","RECOVERY")))

    html = f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <title>Relatório de Run - {esc(os.path.basename(run_dir))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 12px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
    th {{ background: #f2f2f2; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    img {{ max-width: 100%; border: 1px solid #ddd; padding: 6px; background: #fff; }}
    code {{ background: #f7f7f7; padding: 2px 4px; }}
  </style>
</head>
<body>
  <h1>Relatório do Run: {esc(os.path.basename(run_dir))}</h1>

  <p><b>Fonte:</b> <code>http_metrics.csv</code> (TSV sem cabeçalho: ts, endpoint, status, lat_ms, ok)</p>
  <p><b>FIRST_FAILURE (auto):</b> <code>{esc(ff_line)}</code></p>

  <h2>Métricas por endpoint</h2>
  <table>
    <thead>
      <tr>
        <th>Endpoint</th><th>Count</th><th>OK (%)</th><th>Max lat (ms)</th><th>P95 lat (ms)</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>

  <h2>Gráficos</h2>
  <div class="grid">
    <div>
      <h3>OK% por endpoint</h3>
      <img src="ok_rate.png" alt="OK rate">
    </div>
    <div>
      <h3>Latência (p95 vs max)</h3>
      <img src="latency.png" alt="Latency">
    </div>
  </div>

  <div style="margin-top:16px;">
    <h3>Timeline</h3>
    <img src="timeline.png" alt="Timeline">
  </div>

  <h2>Eventos (agregados)</h2>
  <p style="white-space: pre-wrap;">{events_html if events_html else "Sem events.log agregado."}</p>

</body>
</html>
"""
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"[OK] Report criado: {report_path}")

if __name__ == "__main__":
    main()
