#!/usr/bin/env bash
set -e

NS="resilience"
POLICY="allow-api-to-auth"

echo "=== Remover NetworkPolicy $POLICY (simular falha de rede API->Auth) ==="
kubectl -n "$NS" delete networkpolicy "$POLICY"

echo "Aguarda 20s..."
sleep 20

echo "=== Reaplicar NetworkPolicy (recuperação) ==="
kubectl apply -f k8s/04-network-policy.yaml

echo "Fim."