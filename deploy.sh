#!/usr/bin/env bash
set -euo pipefail

echo "Deploying BugSense AI to Kubernetes..."

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v minikube &>/dev/null; then
  echo "minikube is not installed. Install it or adapt this script for your cluster."
  exit 1
fi

if ! minikube status 2>/dev/null | grep -q "Running"; then
  echo -e "${YELLOW}Starting minikube...${NC}"
  minikube start --cpus=4 --memory=8192 --driver=docker
fi

echo -e "${YELLOW}Enabling ingress and metrics-server...${NC}"
minikube addons enable ingress
minikube addons enable metrics-server || true

echo -e "${YELLOW}Using minikube Docker daemon for local images...${NC}"
eval "$(minikube docker-env)"

API_URL="${NEXT_PUBLIC_API_URL:-http://bugsense.local/api/v1}"

echo -e "${YELLOW}Building images (NEXT_PUBLIC_API_URL=${API_URL})...${NC}"
docker build -t bugsense/backend:latest "$ROOT_DIR/apps/api"
docker build -t bugsense/frontend:latest \
  --build-arg "NEXT_PUBLIC_API_URL=${API_URL}" \
  "$ROOT_DIR/apps/web"

echo -e "${YELLOW}Applying manifests...${NC}"
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/resource-quota.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml

echo -e "${YELLOW}Deploying databases...${NC}"
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/chromadb-deployment.yaml

kubectl wait --for=condition=ready pod -l app=postgres -n bugsense --timeout=180s
kubectl wait --for=condition=ready pod -l app=chromadb -n bugsense --timeout=180s || true

echo -e "${YELLOW}Deploying application...${NC}"
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml

kubectl wait --for=condition=ready pod -l app=backend -n bugsense --timeout=300s
kubectl wait --for=condition=ready pod -l app=frontend -n bugsense --timeout=300s

echo -e "${YELLOW}Networking & autoscaling...${NC}"
kubectl apply -f k8s/ingress.yaml
kubectl apply -f k8s/network-policy.yaml || true
kubectl apply -f k8s/hpa.yaml || true

MINIKUBE_IP="$(minikube ip)"
echo -e "${YELLOW}Add this line to your hosts file (or use 'minikube tunnel' for LoadBalancer):${NC}"
echo -e "${GREEN}${MINIKUBE_IP} bugsense.local${NC}"

echo ""
echo -e "${GREEN}Done.${NC}"
echo "kubectl get pods -n bugsense"
echo "Open http://bugsense.local after updating hosts and waiting for ingress."
