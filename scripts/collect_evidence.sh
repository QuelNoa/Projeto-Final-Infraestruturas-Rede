#!/usr/bin/env bash
set -euo pipefail
OUT_DIR="${1:-evidencias}"
NS="${NS:-resilience}"

mkdir -p "$OUT_DIR"

echo "[*] Pods/deployments/services/hpa..."
kubectl -n "$NS" get deploy,svc,pods,hpa -o wide > "$OUT_DIR/cluster_overview.txt"

echo "[*] Events (lastTimestamp)..."
kubectl -n "$NS" get events --sort-by='.lastTimestamp' > "$OUT_DIR/events.txt"

echo "[*] API logs (tail 300 each pod)..."
kubectl -n "$NS" logs -l app=api --tail=300 --timestamps > "$OUT_DIR/api_logs.txt" || true

echo "[*] AUTH logs (tail 300 each pod)..."
kubectl -n "$NS" logs -l app=auth --tail=300 --timestamps > "$OUT_DIR/auth_logs.txt" || true

echo "[*] Ingress-nginx logs with 429/ModSecurity (tail 2000)..."
kubectl -n ingress-nginx logs -l app.kubernetes.io/name=ingress-nginx --tail=2000 --timestamps > "$OUT_DIR/ingress_logs.txt" || true
grep -E " 429 |ModSecurity|OWASP|limit" "$OUT_DIR/ingress_logs.txt" > "$OUT_DIR/ingress_filtered.txt" || true

echo "[*] NetworkPolicies..."
kubectl -n "$NS" get networkpolicy -o yaml > "$OUT_DIR/networkpolicies.yaml"

echo "[*] Evidence collected in $OUT_DIR"
