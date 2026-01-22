#!/usr/bin/env bash
set -euo pipefail
OUT_DIR="${1:-results/run}"
mkdir -p "$OUT_DIR"
echo "[attack] k6 DoS -> /work" | tee "$OUT_DIR/attack.info"
k6 run scripts/k6-dos.js | tee "$OUT_DIR/k6_output.log"
