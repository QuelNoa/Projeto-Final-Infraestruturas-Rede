#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:-}"
if [[ -z "$RUN_DIR" ]]; then
  echo "Uso: $0 <RUN_DIR>" >&2
  exit 1
fi

echo "=== SUMMARY: $RUN_DIR ==="
echo

# k6
K6_JSON="$RUN_DIR/dos/k6_summary.json"
if [[ -f "$K6_JSON" ]]; then
  echo "k6: dos/k6_summary.json"
  # estrutura do teu ficheiro: .metrics.http_reqs.count e .metrics.http_req_duration["p(95)"]
  HTTP_REQS="$(jq -r '.metrics.http_reqs.count // empty' "$K6_JSON" 2>/dev/null || true)"
  P95="$(jq -r '.metrics.http_req_duration["p(95)"] // empty' "$K6_JSON" 2>/dev/null || true)"
  MAX="$(jq -r '.metrics.http_req_duration.max // empty' "$K6_JSON" 2>/dev/null || true)"
  echo " - http_reqs: ${HTTP_REQS:-None}"
  echo " - p95(ms): ${P95:-None}"
  echo " - max(ms): ${MAX:-None}"
else
  echo "k6: (sem k6_summary.json)"
fi

echo

# metrics.json
MJSON="$RUN_DIR/metrics.json"
if [[ ! -f "$MJSON" ]]; then
  echo "erro: missing $MJSON (run calc_resilience_metrics.py first)"
  exit 1
fi

STABLE_N="$(jq -r '.stable_n' "$MJSON")"
POST_W="$(jq -r '.post_window_s' "$MJSON")"
RPO="$(jq -r '.rpo' "$MJSON")"

echo "- recuperação estável: $STABLE_N OK consecutivos"
echo "- janela pós-incidente: ${POST_W}s"
echo "- RPO: $RPO"
echo

echo "Métricas por incidente (por endpoint):"
jq -r '
  .incidents
  | to_entries[]
  | " - \(.key):\n"
    + (
      .value
      | to_entries[]
      | "    • \(.key): MTTD=\(.value.mttd_s // "-")s  MTTR=\(.value.mttr_s // "-")s  RTO=\(.value.rto_s // "-")s"
    )
' "$MJSON"

# overlaps
OV="$(jq -r '.overlaps | length' "$MJSON")"
if [[ "$OV" != "0" ]]; then
  echo
  echo "Aviso: incidentes sobrepostos detetados ($OV). Ver metrics.json/metrics.md."
fi
