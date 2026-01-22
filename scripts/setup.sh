#!/usr/bin/env bash
set -euo pipefail

echo "=== 0) Verificações mínimas ==="
command -v docker >/dev/null || { echo "Falta docker"; exit 1; }
command -v k3d >/dev/null || { echo "Falta k3d"; exit 1; }
command -v kubectl >/dev/null || { echo "Falta kubectl"; exit 1; }
command -v helm >/dev/null || { echo "Falta helm"; exit 1; }

echo "=== 1) Limpeza (se existir) ==="
k3d cluster delete resilient >/dev/null 2>&1 || true

echo "=== 2) /etc/hosts (Linux) ==="
if [[ "$(uname -s)" == "Linux" ]]; then
  sudo sed -i '/resilience\.local/d' /etc/hosts || true
  echo "127.0.0.1 api.resilience.local auth.resilience.local dash.resilience.local grafana.resilience.local" | sudo tee -a /etc/hosts >/dev/null
  echo "OK: hosts configurado"
else
  echo "ATENÇÃO: Em Windows/Mac, tens de editar o ficheiro hosts manualmente:"
  echo "  api.resilience.local auth.resilience.local dash.resilience.local grafana.resilience.local -> 127.0.0.1"
fi

echo "=== 3) Criar cluster k3d (com loadbalancer 80/443) ==="
k3d cluster create resilient \
  -p "80:80@loadbalancer" \
  -p "443:443@loadbalancer" \
  --agents 3 \
  --k3s-arg "--disable=traefik@server:0"

echo "=== 4) Repos Helm ==="
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx >/dev/null
helm repo add jetstack https://charts.jetstack.io >/dev/null
helm repo add grafana https://grafana.github.io/helm-charts >/dev/null
helm repo update >/dev/null

echo "=== 5) Ingress-NGINX ==="
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace --wait

echo "=== 6) cert-manager (CRDs incluídas) ==="
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true --wait

echo "=== 7) Observabilidade (Loki + Promtail + Grafana) ==="
helm install obs grafana/loki-stack \
  --namespace observability --create-namespace \
  --set loki.enabled=true,promtail.enabled=true,grafana.enabled=true \
  --set grafana.adminUser=admin,grafana.adminPassword=admin \
  --wait

echo "=== 8) Build e importar imagens ==="
docker build -t rsl/api:latest services/api
docker build -t rsl/auth:latest services/auth
docker build -t rsl/dashboard:latest services/dashboard
k3d image import rsl/api:latest rsl/auth:latest rsl/dashboard:latest -c resilient

echo "=== 9) Aplicar manifestos Kubernetes ==="
kubectl apply -f k8s/00-namespace.yaml

kubectl apply -f k8s/01-cert-manager-ca.yaml

echo "=== 9.1) Esperar CA secret existir (resilience-root-ca-secret) ==="
kubectl -n resilience wait --for=condition=Ready certificate/resilience-root-ca --timeout=300s

kubectl apply -f k8s/02-certificates.yaml

echo "=== 9.2) Esperar certificados TLS ficarem Ready ==="
kubectl -n resilience wait --for=condition=Ready certificate/auth-internal-tls --timeout=300s
kubectl -n resilience wait --for=condition=Ready certificate/resilience-ingress-cert --timeout=300s

echo "=== 9.3) Confirmar secrets criados ==="
kubectl -n resilience get secret resilience-root-ca-secret auth-internal-tls-secret resilience-ingress-tls

kubectl apply -f k8s/03-services-deployments.yaml
kubectl apply -f k8s/04-network-policies.yaml
kubectl apply -f k8s/05-pdb-hpa.yaml
kubectl apply -f k8s/06-ingress.yaml

echo "=== 10) Esperar pods prontos ==="
kubectl -n resilience wait --for=condition=ready pod -l tier=app --timeout=240s

echo "=== SETUP OK ==="
echo "URLs (self-signed, o browser vai avisar):"
echo "  https://api.resilience.local/ping"
echo "  https://dash.resilience.local/"
echo "  https://grafana.resilience.local/  (admin/admin)"
