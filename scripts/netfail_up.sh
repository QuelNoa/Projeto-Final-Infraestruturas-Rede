#!/usr/bin/env bash
set -euo pipefail
# Remove a policy deny temporária
kubectl -n resilience delete networkpolicy deny-api-to-auth-temporary >/dev/null 2>&1 || true
echo "netfail: deny removed"
