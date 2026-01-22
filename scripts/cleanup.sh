#!/usr/bin/env bash
set -euo pipefail
k3d cluster delete resilient >/dev/null 2>&1 || true
docker rmi rsl/api:latest rsl/auth:latest rsl/dashboard:latest >/dev/null 2>&1 || true
echo "Limpeza concluída."
