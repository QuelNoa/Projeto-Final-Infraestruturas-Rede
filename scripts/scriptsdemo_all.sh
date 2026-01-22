#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="results/demo_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RUN_DIR"

export CURL_INSECURE=1

# 1) iniciar monitor em background
./scripts/monitor_http.sh https://api.resilience.local 1 "$RUN_DIR" &
MON_PID=$!

cleanup() { kill $MON_PID >/dev/null 2>&1 || true; }
trap cleanup EXIT

echo "[*] Monitor PID=$MON_PID run_dir=$RUN_DIR"
sleep 3

# 2) incidentes
./scripts/run_incident.sh dos "$RUN_DIR/dos"
sleep 5

./scripts/run_incident.sh kill_api "$RUN_DIR/kill"
sleep 5

./scripts/run_incident.sh netfail "$RUN_DIR/netfail"
sleep 5

# 3) recolher evidências e sumário
./scripts/collect_evidence.sh "$RUN_DIR/evidencias"
./scripts/summarize_run.sh "$RUN_DIR" | tee "$RUN_DIR/summary.txt"

echo "[OK] Run completo em $RUN_DIR"

