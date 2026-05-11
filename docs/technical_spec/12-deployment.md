# Technical Spec: Deployment

## Overview

Design the deployment strategy for development, staging, and production
environments. The system consists of: backend API, frontend SPA, PostgreSQL,
Qdrant, Redis, Celery workers.

---

## Development Environment

**[DECISION: Local dev setup]**

Choices:
- A) **Docker Compose for services (PostgreSQL, Qdrant, Redis) + running
  backend/frontend natively for hot reload** — fast iteration, services
  are stable. **(Recommended)**
- B) All-in Docker Compose — uniform environment, slower inner loop
- C) All native (no Docker) — install everything locally

**docker-compose.dev.yml services:**

    services:
      postgres:
        image: postgres:16
        ports: ["5432:5432"]
        volumes: [pgdata:/var/lib/postgresql/data]
        environment:
          POSTGRES_DB: mycoai
          POSTGRES_USER: mycoai
          POSTGRES_PASSWORD: devpassword

      qdrant:
        image: qdrant/qdrant:latest
        ports: ["6333:6333", "6334:6334"]
        volumes: [qdrant_storage:/qdrant/storage]

      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]

    Backend: uv --directory repos/mycoai_retrieval_backend run uvicorn
    Frontend: pnpm --dir repos/mycoai_retrieval_frontend dev (port 5173)
    Celery: uv --directory repos/mycoai_retrieval_backend run celery worker

---

## Production Deployment

**[DECISION: Production deployment strategy]**

Choices:
- A) **Docker Compose on single VM** — all services in containers.
  Simple, cheap, good for <100 concurrent users. **(Recommended for MVP)**
- B) Vast.ai GPU instance + separate API VM — GPU for training, API
  server for serving. More complex, better for training.
- C) Kubernetes (k3s) — scalable, heavy for MVP
- D) Fly.io / Railway / Render — managed, less control, good for early
  stage

**Production docker-compose.yml services:**

    services:
      postgres:  (same as dev, with persistent volume)
      qdrant:    (same as dev, with persistent volume)
      redis:     (same as dev)
      backend:
        build: repos/mycoai_retrieval_backend
        ports: ["8000:8000"]
        depends_on: [postgres, qdrant, redis]
        environment: [...]
      celery-worker:
        build: repos/mycoai_retrieval_backend
        command: celery -A mycoai_retrieval_backend.tasks worker
        depends_on: [redis, postgres]
      frontend:
        build: repos/mycoai_retrieval_frontend
        ports: ["80:80"]
        depends_on: [backend]

---

## Environment Variables

**[DECISION: Secrets management]**

Choices:
- A) **`.env` file (dev) + Docker secrets (production)** — standard
  pattern, simple, works with Docker Compose **(Recommended)**
- B) HashiCorp Vault — production-grade, heavy for MVP
- C) Cloud provider secrets manager (AWS/GCP) — if on cloud

**Required environment variables:**

| Variable | Description |
|----------|-------------|
| `MYCOAI_BACKEND_ENVIRONMENT` | "development" | "production" |
| `MYCOAI_BACKEND_HOST` | Bind address |
| `MYCOAI_BACKEND_PORT` | Bind port |
| `MYCOAI_QDRANT_HOST` | Qdrant host |
| `MYCOAI_QDRANT_PORT` | Qdrant REST port |
| `MYCOAI_QDRANT_COLLECTION` | Collection name |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `JWT_SECRET` | HS256 signing key |
| `JWT_ALGORITHM` | "HS256" |
| `JWT_ACCESS_EXPIRE_MINUTES` | 60 |
| `CORS_ORIGINS` | Frontend URL(s), comma-separated |
| `UPLOAD_DIR` | Upload storage path |
| `WEIGHTS_DIR` | Model weights path |

---

## CI/CD Pipeline

**[DECISION: CI/CD workflow]**

### CI (GitHub Actions, on push/PR):

    1. Backend:
       - ruff check + format check
       - mypy (strict)
       - pytest
    2. Frontend:
       - ESLint
       - Prettier check
       - TypeScript typecheck
       - Build (vite build)
    3. Docker image build (dry run)

### CD (on merge to main):

    **[DECISION: CD strategy]**

    Choices:
    - A) **Manual deploy** — CI builds + tests, human triggers deploy
      via SSH to VM + docker compose pull && up **(Recommended for MVP)**
    - B) Auto-deploy on merge — fully automated, risky without staging
    - C) Staging environment first — deploy to staging, smoke test,
      promote to production

---

## Infrastructure

**[DECISION: VM / server specification]**

**Minimum for MVP (no GPU training on same machine):**

| Component | Spec |
|-----------|------|
| CPU | 4 vCPUs |
| RAM | 8 GB |
| Storage | 100 GB SSD |
| OS | Ubuntu 22.04 or 24.04 |

**With GPU (for training):**

| Component | Spec |
|-----------|------|
| CPU | 8 vCPUs |
| RAM | 32 GB |
| GPU | NVIDIA T4 / RTX 3090 / A4000 |
| Storage | 200 GB SSD |

**[DECISION: Training infrastructure]**

Choices:
- A) **Vast.ai GPU instance (on-demand) for training, CPU VM for
  serving** — separates concerns, cost-optimized **(Recommended)**
- B) Same VM for everything — simpler, needs GPU on main server
- C) Cloud GPU (AWS/GCP) — managed, expensive

---

## Backup Strategy

**[DECISION: Backup strategy]**

Choices:
- A) **Database dumps (daily) + file storage sync (rclone) + Qdrant
  snapshots (weekly)** — covers all data. Use existing rclone setup
  for Dataset/ and weights/. **(Recommended)**
- B) PostgreSQL only — files assumed re-creatable
- C) Full VM snapshot — simple, expensive storage

| What | How | Frequency |
|------|-----|-----------|
| PostgreSQL | pg_dump | Daily |
| Uploaded images | rclone sync to Google Drive | Daily |
| Model weights | rclone sync to Google Drive | On change |
| Qdrant | Snapshot API | Weekly |
| Qdrant for re-index recovery | Re-index from scratch | (last resort) |

---

## Monitoring

**[DECISION: Monitoring approach]**

Choices:
- A) **Healthcheck endpoints + Docker health checks + logs** — minimal
  but sufficient for MVP. Alert on /health failure. **(Recommended)**
- B) Prometheus + Grafana — production-grade, more setup
- C) Sentry for error tracking + UptimeRobot for availability
- D) None — fix when broken

---

## Scaling Notes (Future)

| Component | Scale strategy |
|-----------|---------------|
| Backend API | Horizontal: multiple replicas behind nginx |
| Celery workers | Horizontal: more workers for batch jobs |
| PostgreSQL | Vertical first, then read replicas |
| Qdrant | Qdrant cluster with sharding |
| Redis | Cluster mode or managed (ElastiCache) |
| File storage | Migrate to S3-compatible |

---

## Security Checklist

- [ ] PostgreSQL not exposed to internet (Docker internal network)
- [ ] Qdrant not exposed to internet
- [ ] Redis not exposed to internet
- [ ] Rate limiting on auth endpoints
- [ ] CORS restricted to known origins
- [ ] File upload size limits (50MB)
- [ ] HTTPS (via reverse proxy: nginx + Let's Encrypt)
- [ ] Environment variables for all secrets (no hardcoded)
- [ ] Docker images rebuilt on security updates
- [ ] Regular database backups with tested restore procedure
