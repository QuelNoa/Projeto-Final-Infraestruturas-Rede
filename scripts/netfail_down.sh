#!/usr/bin/env bash
set -euo pipefail
# Aplica DENY (bloqueia tudo no api egress), simulando falha api->auth
kubectl -n resilience apply -f k8s/04-network-policies.yaml >/dev/null
kubectl -n resilience patch networkpolicy deny-api-to-auth-temporary -p '{}' >/dev/null
echo "netfail: deny applied"
