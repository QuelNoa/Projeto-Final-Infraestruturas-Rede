#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${1:-results/kill_run}"
NAMESPACE="${NAMESPACE:-resilience}"
BASE_URL="${BASE_URL:-https://api.resilience.local}"
INTERVAL="${INTERVAL:-1}"

mkdir -p "$OUT_DIR"
EVENTS="$OUT_DIR/events.log"
CURL_FLAGS=(-sS)
[[ "${CURL_INSECURE:-1}" == "1" ]] && CURL_FLAGS+=(-k)

log(){ echo "[$(date -Is)] $*" | tee -a "$EVENTS" ; }

# Escolhe um pod
POD="$(kubectl -n "$NAMESPACE" get pod -l app=api -o jsonpath='{.items[0].metadata.name}')"

log "INCIDENT_START type=kill_api pod=$POD"
T0="$(date -Is)"

kubectl -n "$NAMESPACE" delete pod "$POD" --force --grace-period=0 >/dev/null 2>&1 || true

# Espera até /ping estar OK de forma contínua (3 sucessos seguidos)
ok_streak=0
while true; do
  code="$(curl "${CURL_FLAGS[@]}" -o /dev/null -w "%{http_code}" "$BASE_URL/ping" || echo 000)"
  ts="$(date -Is)"
  echo "$ts,/ping,$code" >> "$OUT_DIR/ping_watch.log"
  if [[ "$code" =~ ^2 ]]; then
    ok_streak=$((ok_streak+1))
  else
    ok_streak=0
  fi
  if [[ "$ok_streak" -ge 3 ]]; then
    break
  fi
  sleep "$INTERVAL"
done

T3="$(date -Is)"
log "RECOVERED type=kill_api ping_ok_streak=3"
log "INCIDENT_END type=kill_api"

python3 - <<PY
from datetime import datetime
t0=datetime.fromisoformat("$T0".replace("Z","+00:00"))
t3=datetime.fromisoformat("$T3".replace("Z","+00:00"))
print(f"RTO_SECONDS={(t3-t0).total_seconds():.2f}")
PY | tee -a "$OUT_DIR/rto.txt"
