#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# demo_all.sh
#  - corre um run completo (monitor + 3 incidentes + evidências + report + summary)
#
# Requisitos:
#  - scripts/monitor_http.sh
#  - scripts/preflight.sh
#  - scripts/run_incident.sh
#  - scripts/collect_evidence.sh
#  - scripts/summarize_run.sh
#  - scripts/make_report.py
#
# Variáveis úteis:
#  - BASE_URL (default: https://api.resilience.local)
#  - PAUSE=1 (default) -> pede ENTER entre etapas; PAUSE=0 corre direto
#  - CURL_INSECURE=1 (default neste script) para cert self-signed do Ingress
#  - CURL_CA=/caminho/ca.crt (alternativa a insecure)
#  - NETFAIL_SECONDS=20 (default) para duração do netfail
#  - ALLOW_API_TO_AUTH_YAML (caminho do YAML original allow-api-to-auth)
# -----------------------------------------------------------------------------

BASE_URL="${BASE_URL:-https://api.resilience.local}"
PAUSE="${PAUSE:-1}"

pause() {
  if [[ "$PAUSE" == "1" ]]; then
    read -r -p ">> ENTER para continuar..." _
  fi
}

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "[ERRO] Falta comando: $1" >&2; exit 1; }
}

# sanity checks
need kubectl
need python3

if [[ ! -x "./scripts/monitor_http.sh" ]]; then echo "[ERRO] ./scripts/monitor_http.sh não existe ou não é executável"; exit 1; fi
if [[ ! -x "./scripts/preflight.sh" ]]; then echo "[ERRO] ./scripts/preflight.sh não existe ou não é executável"; exit 1; fi
if [[ ! -x "./scripts/run_incident.sh" ]]; then echo "[ERRO] ./scripts/run_incident.sh não existe ou não é executável"; exit 1; fi
if [[ ! -x "./scripts/collect_evidence.sh" ]]; then echo "[ERRO] ./scripts/collect_evidence.sh não existe ou não é executável"; exit 1; fi
if [[ ! -x "./scripts/summarize_run.sh" ]]; then echo "[ERRO] ./scripts/summarize_run.sh não existe ou não é executável"; exit 1; fi
if [[ ! -f "./scripts/make_report.py" ]]; then echo "[ERRO] ./scripts/make_report.py não existe"; exit 1; fi

# Run dir
RUN_DIR="results/demo_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN_DIR"

# TLS: default para self-signed no Ingress
# Se preferires CA real, exporta CURL_CA=/path/ca.crt e põe CURL_INSECURE=0
export CURL_INSECURE="${CURL_INSECURE:-1}"

echo "[*] RUN_DIR=$RUN_DIR"
echo "[*] BASE_URL=$BASE_URL"
echo "[*] PAUSE=$PAUSE"
echo "[*] CURL_INSECURE=${CURL_INSECURE}"
echo "[*] NETFAIL_SECONDS=${NETFAIL_SECONDS:-20}"
echo "[*] ALLOW_API_TO_AUTH_YAML=${ALLOW_API_TO_AUTH_YAML:-k8s/networkpolicies/allow-api-to-auth.yaml}"
echo

# 1) Monitor
./scripts/monitor_http.sh "$BASE_URL" 1 "$RUN_DIR" &
MON_PID=$!

cleanup() {
  echo
  echo "[*] A terminar monitor (PID=$MON_PID)..."
  kill "$MON_PID" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "[*] Monitor iniciado (PID=$MON_PID)."
pause

# 2) Preflight inicial (baseline)
echo "[*] Preflight (baseline)..."
./scripts/preflight.sh | tee "$RUN_DIR/preflight_baseline.log"
pause

# 3) DoS
echo "[*] Incidente: dos"
mkdir -p "$RUN_DIR/dos"
./scripts/preflight.sh | tee "$RUN_DIR/dos/preflight.log"
./scripts/run_incident.sh dos "$RUN_DIR/dos"
pause

# 4) Kill API pod
echo "[*] Incidente: kill_api"
mkdir -p "$RUN_DIR/kill"
./scripts/preflight.sh | tee "$RUN_DIR/kill/preflight.log"
./scripts/run_incident.sh kill_api "$RUN_DIR/kill"
pause

# 5) Netfail (API->Auth)
echo "[*] Incidente: netfail"
mkdir -p "$RUN_DIR/netfail"
./scripts/preflight.sh | tee "$RUN_DIR/netfail/preflight.log"
./scripts/run_incident.sh netfail "$RUN_DIR/netfail"
pause

# 6) Evidências + Report + Summary
echo "[*] A recolher evidências..."
./scripts/collect_evidence.sh "$RUN_DIR/evidencias"
python3 scripts/make_report.py "$RUN_DIR"

python3 scripts/calc_resilience_metrics.py "$RUN_DIR"
python3 scripts/write_metrics_md.py "$RUN_DIR"

./scripts/summarize_run.sh "$RUN_DIR" | tee "$RUN_DIR/summary.txt"
echo
echo "[OK] Run completo."
echo " - Pasta:   $RUN_DIR"
echo " - Report:  $RUN_DIR/report.html"
echo " - Summary: $RUN_DIR/summary.txt"
