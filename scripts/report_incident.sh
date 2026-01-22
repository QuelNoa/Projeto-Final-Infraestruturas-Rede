#!/bin/bash
echo "--- RELATÓRIO DE RESILIÊNCIA ---"
echo "Data: $(date)"
echo ""
echo "1. VERIFICAÇÃO DE REPLICAÇÃO (Mínimo 3):"
kubectl -n resilience get deployments -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas
echo ""
echo "2. ÚLTIMOS EVENTOS DE RECUPERAÇÃO (Self-healing):"
kubectl -n resilience get events --sort-by='.lastTimestamp' | tail -n 5
echo ""
echo "3. MÉTRICAS DE CARGA (HPA):"
kubectl -n resilience get hpa api-hpa