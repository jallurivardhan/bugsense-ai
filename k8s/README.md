# BugSense AI — Kubernetes deployment

Manifests and scripts to run **BugSense AI** (Next.js frontend + FastAPI backend + PostgreSQL + ChromaDB) on Kubernetes.

## Architecture

```text
                    ┌─────────────────┐
                    │  Ingress (nginx) │
                    │  bugsense.local  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
     ┌────────▼────────┐           ┌───────▼────────┐
     │ frontend-service │           │ backend-service │
     │   (Next.js x2)   │           │  (FastAPI x2)   │
     └──────────────────┘           └───────┬────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         │                    │                    │
                 ┌───────▼───────┐    ┌───────▼───────┐    ┌────────▼────────┐
                 │ postgres-svc  │    │ chromadb-svc  │    │ Internet :443  │
                 │   PostgreSQL  │    │    Chroma     │    │ OpenAI / Groq   │
                 └───────────────┘    └───────────────┘    └─────────────────┘
```

- **Ingress**: `bugsense.local` — `/api` → backend (port 8000), `/` → frontend (port 3000).
- **Backend** reads `DATABASE_URL`, `CHROMA_HOST` / `CHROMA_PORT`, API keys, `CORS_ORIGINS`, `OLLAMA_BASE_URL` (optional; no Ollama workload is included by default).
- **Chroma**: When `CHROMA_HOST` is set, the API uses `chromadb.HttpClient` instead of a local persistent directory.

## Prerequisites

- `kubectl` configured (e.g. minikube, kind, or a cloud cluster).
- Default StorageClass for PVCs (dynamic provisioning).
- For **HPA**: metrics-server installed (`minikube addons enable metrics-server`).
- For **Ingress**: NGINX Ingress Controller and class `nginx`.

## Security (before production)

1. Edit **`k8s/secrets.yaml`**: strong `DATABASE_PASSWORD`, matching `DATABASE_URL`, and real `OPENAI_API_KEY` / `GROQ_API_KEY` as needed.
2. Do **not** commit real secrets; use Sealed Secrets, External Secrets, or your cloud secret manager.
3. Replace **`bugsense.local`** with your domain and TLS (e.g. cert-manager + `Ingress` TLS block).

## Frontend API URL (`NEXT_PUBLIC_*`)

`NEXT_PUBLIC_API_URL` is **embedded at Docker build time**. The default image build uses:

`http://bugsense.local/api/v1`

Rebuild the frontend image if your public URL differs:

```bash
docker build -t bugsense/frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1 \
  ./apps/web
```

Runtime `env` on the Deployment does not change already-built client bundles.

## Quick start (minikube)

From the **repository root**:

```bash
chmod +x deploy.sh
./deploy.sh
```

Add to `/etc/hosts` (or `C:\Windows\System32\drivers\etc\hosts`):

```text
<minikube-ip> bugsense.local
```

Wait for the ingress controller to assign an address (`kubectl get ingress -n bugsense`), then open **http://bugsense.local**.

## Apply manifests manually

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/resource-quota.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/persistent-volumes.yaml
kubectl apply -f k8s/postgres-deployment.yaml
kubectl apply -f k8s/chromadb-deployment.yaml
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/frontend-deployment.yaml
kubectl apply -f k8s/ingress.yaml
# Optional:
kubectl apply -f k8s/network-policy.yaml
kubectl apply -f k8s/hpa.yaml
```

## Network policies

`k8s/network-policy.yaml` restricts backend ingress to the **frontend** pods and the **ingress-nginx** namespace (label `kubernetes.io/metadata.name: ingress-nginx`). If your controller uses different labels/namespaces, adjust the rule or skip applying this file.

Egress allows PostgreSQL, Chroma, DNS (UDP 53), and HTTP/S to the internet for cloud LLM APIs.

## Ollama

`OLLAMA_HOST` in the ConfigMap points at `http://ollama-service:11434`, but **no Ollama Deployment is included**. Deploy Ollama separately or change `OLLAMA_BASE_URL` / `AI_PROVIDER` to use OpenAI or Groq only.

## Resource notes

- The API **Docker image** includes heavy ML dependencies (e.g. PyTorch via `requirements.txt`); builds can be large and slow. Consider a slim requirements split for production if you do not need local embedding models in the API container.
- **HPA** `minReplicas: 2` assumes a cluster that can schedule two backend and two frontend pods under the namespace **ResourceQuota**.

## Files

| File | Purpose |
|------|---------|
| `namespace.yaml` | `bugsense` namespace |
| `configmap.yaml` | Non-secret config (DB name, Chroma host, CORS JSON, flags) |
| `secrets.yaml` | DB URL, passwords, API keys (edit before use) |
| `persistent-volumes.yaml` | PVCs for Postgres and Chroma |
| `postgres-deployment.yaml` | PostgreSQL + Service |
| `chromadb-deployment.yaml` | Chroma server + Service |
| `backend-deployment.yaml` | FastAPI + Service |
| `frontend-deployment.yaml` | Next.js standalone + Service |
| `ingress.yaml` | Single host routing `/api` and `/` |
| `hpa.yaml` | CPU/memory autoscaling |
| `network-policy.yaml` | Optional hardening |
| `resource-quota.yaml` | Namespace quotas |

## Dockerfiles

- `apps/api/Dockerfile` — Python 3.11, `uvicorn`, health check on `/api/v1/health`.
- `apps/web/Dockerfile` — multi-stage build, `output: 'standalone'` from `next.config.ts`.
