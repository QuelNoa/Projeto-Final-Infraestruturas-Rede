#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# run_incident.sh
#  - executa um "incidente" (dos / kill_api / netfail / ...) e guarda evidências
#  - cria markers em <out_dir>/events.log (auditoria + parsing)
#
# Uso:
#   ./scripts/run_incident.sh <tipo> <out_dir>
#
# Exemplos:
#   ./scripts/run_incident.sh dos results/manual_dos
#   ./scripts/run_incident.sh kill_api results/manual_kill
#   ./scripts/run_incident.sh netfail results/manual_netfail
# -----------------------------------------------------------------------------

TYPE="${1:-}"
OUT_DIR="${2:-}"

if [[ -z "$TYPE" || -z "$OUT_DIR" ]]; then
  echo "Uso: $0 <tipo> <out_dir>"
  exit 1
fi

# -----------------------------------------------------------------------------
# Config base (ajusta se necessário)
# -----------------------------------------------------------------------------
NS="${NS:-resilience}"

API_LABEL="${API_LABEL:-app=api}"
AUTH_LABEL="${AUTH_LABEL:-app=auth}"

INGRESS_NS="${INGRESS_NS:-ingress-nginx}"
INGRESS_LABEL="${INGRESS_LABEL:-app.kubernetes.io/name=ingress-nginx}"

K6_SCRIPT="${K6_SCRIPT:-scripts/k6-dos.js}"

# Netfail: vamos remover e restaurar a policy que permite api -> auth
ALLOW_API_TO_AUTH_POLICY="${ALLOW_API_TO_AUTH_POLICY:-allow-api-to-auth}"
ALLOW_API_TO_AUTH_YAML="${ALLOW_API_TO_AUTH_YAML:-k8s/networkpolicies/allow-api-to-auth.yaml}"

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------
mkdir -p "$OUT_DIR"
EVENTS="$OUT_DIR/events.log"
: > "$EVENTS"

log_event() {
  # ISO-8601 com timezone, consistente para parsing
  local ts
  ts="$(date -Iseconds)"
  echo "[$ts] $*" | tee -a "$EVENTS" >/dev/null
}

run_cmd() {
  # Regista comandos para reprodutibilidade
  local cmd="$*"
  echo "+ $cmd" >> "$OUT_DIR/commands.log"
  eval "$cmd"
}

ensure_namespace_exists() {
  if ! kubectl get ns "$NS" >/dev/null 2>&1; then
    echo "Namespace '$NS' não existe." >&2
    exit 1
  fi
}

pick_one_pod_by_label() {
  local label="$1"
  kubectl -n "$NS" get pod -l "$label" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true
}

# -----------------------------------------------------------------------------
# Incidente: DoS (k6)
# -----------------------------------------------------------------------------
incident_dos() {
  log_event "INCIDENT_START type=dos"

  if [[ ! -f "$K6_SCRIPT" ]]; then
    echo "k6 script não encontrado: $K6_SCRIPT" >&2
    exit 1
  fi

  # Guarda output completo + JSON de summary
  run_cmd "k6 run --summary-export \"$OUT_DIR/k6_summary.json\" \"$K6_SCRIPT\" | tee \"$OUT_DIR/k6_output.log\""

  log_event "INCIDENT_END type=dos"
}

# -----------------------------------------------------------------------------
# Incidente: kill_api (matar 1 pod da API)
#  - IMPORTANTE: pode não haver falha funcional (3 réplicas), por isso:
#    medimos "recuperação infra" via rollout status
# -----------------------------------------------------------------------------
incident_kill_api() {
  log_event "INCIDENT_START type=kill_api"

  local pod
  pod="$(pick_one_pod_by_label "$API_LABEL")"
  if [[ -z "$pod" ]]; then
    echo "Não encontrei pod API com label '$API_LABEL' em ns=$NS" >&2
    exit 1
  fi

  log_event "ACTION deleting_one_api_pod pod=$pod"
  run_cmd "kubectl -n \"$NS\" delete pod \"$pod\" --force --grace-period=0"

  # PATCH: medir recuperação infra (Deployment voltar a Ready)
  log_event "ACTION waiting_for_api_rollout deployment=api"
  run_cmd "kubectl -n \"$NS\" rollout status deployment/api --timeout=120s"
  log_event "RECOVERED_INFRA type=kill_api deployment=api"

  log_event "INCIDENT_END type=kill_api"
}

# -----------------------------------------------------------------------------
# Incidente: netfail (quebrar API -> Auth)
#  - PATCH: remover temporariamente a allow-api-to-auth e restaurar o YAML original
#  - Isto força /secure-data a falhar (503), enquanto /ping pode continuar OK
# -----------------------------------------------------------------------------
incident_netfail() {
  log_event "INCIDENT_START type=netfail"

  local ALLOW_NAME="allow-api-to-auth"
  local BACKUP_YAML="$OUT_DIR/${ALLOW_NAME}.backup.yaml"

  # backup
  kubectl -n "$NS" get networkpolicy "$ALLOW_NAME" -o yaml > "$BACKUP_YAML" 2>/dev/null || true

  # cortar rede (delete da allow)
  log_event "ACTION delete_allow_policy name=$ALLOW_NAME"
  run_cmd "kubectl -n \"$NS\" delete networkpolicy \"$ALLOW_NAME\" --ignore-not-found=true"

  local secs="${NETFAIL_SECONDS:-20}"
  log_event "ACTION netfail_sleep seconds=$secs"
  sleep "$secs"

  # restore
  log_event "ACTION restore_allow_policy name=$ALLOW_NAME"
  if [[ -s "$BACKUP_YAML" ]]; then
    run_cmd "kubectl -n \"$NS\" apply -f \"$BACKUP_YAML\""
  else
    echo "ERRO: não existia '$ALLOW_NAME' para fazer backup, e sem backup não sei restaurar." >&2
    exit 1
  fi

log_event "INCIDENT_END type=netfail"
} 

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
ensure_namespace_exists

case "$TYPE" in
  dos)
    incident_dos
    ;;
  kill_api)
    incident_kill_api
    ;;
  netfail)
    incident_netfail
    ;;
  *)
    echo "Tipo de incidente desconhecido: $TYPE"
    echo "Tipos suportados: dos | kill_api | netfail"
    exit 1
    ;;
esac
