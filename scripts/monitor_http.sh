#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   ./scripts/monitor_http.sh https://api.resilience.local 1 results/run1
#
# Requisitos:
#   - curl
#
# Nota:
#   - Se usas cert self-signed no Ingress, usa CURL_INSECURE=1
#   - Se tens CA, podes passar CURL_CA=/path/ca.crt

BASE_URL="${1:?BASE_URL (ex: https://api.resilience.local)}"
INTERVAL_SEC="${2:-1}"
OUT_DIR="${3:-results/run}"

mkdir -p "$OUT_DIR"

CSV="$OUT_DIR/http_metrics.csv"
EVENTS="$OUT_DIR/events.log"

CURL_FLAGS=()
if [[ "${CURL_INSECURE:-0}" == "1" ]]; then
  CURL_FLAGS+=(-k)
fi
if [[ -n "${CURL_CA:-}" ]]; then
  CURL_FLAGS+=(--cacert "$CURL_CA")
fi

echo "ts_iso,endpoint,http_code,lat_ms,ok" > "$CSV"
echo "[$(date -Is)] monitor started base_url=$BASE_URL interval=${INTERVAL_SEC}s" | tee -a "$EVENTS"

# Estado para MTTD/MTTR (simples e eficaz)
INCIDENT_ACTIVE=0
T_FIRST_FAIL=""
T_RECOVER=""

measure() {
  local endpoint="$1"
  local url="${BASE_URL}${endpoint}"

  # curl format: http_code + total_time
  # total_time em segundos com decimais
  local out
  out="$(curl -sS "${CURL_FLAGS[@]}" -o /dev/null -w "%{http_code} %{time_total}" "$url" || echo "000 9.999")"
  local code time_s
  code="$(awk '{print $1}' <<<"$out")"
  time_s="$(awk '{print $2}' <<<"$out")"

  # converter segundos -> ms (inteiro)
  local lat_ms
  lat_ms="$(awk -v t="$time_s" 'BEGIN { printf("%d", t*1000) }')"

  local ok=0
  if [[ "$code" =~ ^2[0-9][0-9]$ ]]; then ok=1; fi

  local ts
  ts="$(date -Is)"
  echo "$ts,$endpoint,$code,$lat_ms,$ok" >> "$CSV"

  # lógica de incidente: consideramos falha se /ping falhar OU /secure-data falhar
  # (vais chamar measure para os dois)
  echo "$ok"
}

while true; do
  # mede endpoints chave
  ok_ping="$(measure /ping)"
  ok_secure="$(measure /secure-data)"

  # incidente se algum falhar
  if [[ "$ok_ping" == "0" || "$ok_secure" == "0" ]]; then
    if [[ "$INCIDENT_ACTIVE" == "0" ]]; then
      INCIDENT_ACTIVE=1
      T_FIRST_FAIL="$(date -Is)"
      echo "[$T_FIRST_FAIL] FIRST_FAILURE ping_ok=$ok_ping secure_ok=$ok_secure" | tee -a "$EVENTS"
    fi
  else
    if [[ "$INCIDENT_ACTIVE" == "1" ]]; then
      INCIDENT_ACTIVE=0
      T_RECOVER="$(date -Is)"
      echo "[$T_RECOVER] RECOVERED ping_ok=$ok_ping secure_ok=$ok_secure" | tee -a "$EVENTS"
    fi
  fi

  sleep "$INTERVAL_SEC"
done
