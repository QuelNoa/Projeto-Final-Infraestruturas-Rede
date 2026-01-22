#!/usr/bin/env bash
set -euo pipefail

ns="resilience"

echo "[preflight] DNS resolve auth"
kubectl -n "$ns" exec deploy/api -- sh -c '
python - << "PY"
import socket
print("auth ->", socket.gethostbyname("auth"))
PY
'

echo "[preflight] TCP connect auth:8000"
kubectl -n "$ns" exec deploy/api -- sh -c '
python - << "PY"
import socket
ip=socket.gethostbyname("auth")
s=socket.socket(); s.settimeout(2)
s.connect((ip,8000))
print("CONNECT OK", ip, 8000)
PY
'

echo "[preflight] OK"
