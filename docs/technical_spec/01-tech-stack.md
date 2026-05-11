# Technical Spec: Technology Stack

## Overview

Choose the technology stack for backend, frontend, database, vector store,
file storage, and deployment. This document records decisions — each marked
with [DECISION] and a multiple-choice prompt.

---

## Backend Framework

The backend is already scaffolded with FastAPI.

**[DECISION: Backend framework]**

Choices:
- A) **FastAPI** (already in use, async-native, Pydantic integration,
  auto-docs, good for ML/API workloads) **(Recommended)**
- B) Flask + Celery (simpler but less async support)
- C) Django + DRF (heavier, admin panel included)

---

## Database

Currently no database. Need to choose an ORM + DB engine.

**[DECISION: Database engine]**

Choices:
- A) **PostgreSQL** — production-grade, supports vector extensions
  (pgvector), full-text search, JSONB **(Recommended)**
- B) SQLite — zero-config, good for dev, not for concurrent writes
- C) MySQL/MariaDB — similar to PostgreSQL but fewer vector/JSON features

**[DECISION: ORM / DB access layer]**

Choices:
- A) **SQLAlchemy 2.0 (async)** — mature ORM, async support, Alembic
  migrations **(Recommended)**
- B) Tortoise ORM — async-native, Django-style, less ecosystem
- C) Raw asyncpg / psycopg — no ORM, manual SQL
- D) Prisma (Node.js) — if sharing schema with frontend

**[DECISION: Migration tool]**

Choices:
- A) **Alembic** (pairs with SQLAlchemy) **(Recommended)**
- B) Manual SQL scripts
- C) Django migrations (only with Django)

---

## Vector Database

Qdrant is already used by fungal-cv-qdrant experiments.

**[DECISION: Vector database]**

Choices:
- A) **Qdrant** — already in use, cosine distance, named vectors,
  rich filtering, Rust-based performance **(Recommended)**
- B) pgvector (PostgreSQL extension) — one less service, simpler ops
- C) Milvus — more features, heavier operations

**[DECISION: Qdrant deployment mode]**

Choices:
- A) **Docker Compose** (development + small production)
  **(Recommended for now)**
- B) Qdrant Cloud (managed, pay-per-use)
- C) Self-hosted on dedicated VM
- D) Embedded mode (in-process, no separate server)

---

## File / Image Storage

Need to store uploaded images, segmented crops, and model weights.

**[DECISION: File storage]**

Choices:
- A) **Local filesystem** — simple, already the pattern in fungal-cv-qdrant
  (e.g. Dataset/, weights/) **(Recommended for now)**
- B) S3-compatible object storage (MinIO, AWS S3) — scalable, cloud-ready
- C) Google Cloud Storage — if already on GCP

**[DECISION: Image processing pipeline]**

Choices:
- A) **OpenCV + NumPy** (already used by fungal-cv-qdrant experiments)
  **(Recommended)**
- B) Pillow — simpler but slower for CV operations
- C) Cloud function / GPU serverless — heavy ops offloaded

---

## Frontend Framework

Already scaffolded with React 19 + Vite + shadcn/ui + Tailwind v4.

**[DECISION: Frontend routing]**

Choices:
- A) **React Router v7** — standard SPA routing, file-based or
  config-based **(Recommended)**
- B) TanStack Router — type-safe, search-params native
- C) No router (single-page app with conditional rendering)

**[DECISION: Server state / data fetching]**

Choices:
- A) **TanStack Query (React Query)** — caching, retry, background
  refetch, devtools **(Recommended)**
- B) SWR — simpler, fewer features
- C) useEffect + fetch — no library, manual caching

**[DECISION: Form handling]**

Choices:
- A) **React Hook Form + Zod** — performant, type-safe validation
  **(Recommended)**
- B) Formik + Yup — similar, slightly heavier
- C) Native HTML forms + manual validation

**[DECISION: Charting / Graph visualization]**

Choices:
- A) **Recharts** (for pie/bar/line charts) + **D3.js** (for KNN graph)
  **(Recommended)**
- B) ECharts — all-in-one, heavier bundle
- C) Chart.js — simpler, fewer visualization options
- D) Nivo — React-native D3 wrappers

**[DECISION: File upload component]**

Choices:
- A) **react-dropzone** — drag-and-drop, preview, widely used
  **(Recommended)**
- B) Uppy — more features (tus, resumable), heavier
- C) Custom input[type=file] — simplest, least UX

**[DECISION: Image annotation (bounding boxes)]**

Choices:
- A) **Custom canvas/SVG overlay** on image — lightweight, full
  control, shadcnui-compatible **(Recommended)**
- B) react-konva — Canvas-based, good for complex annotations
- C) Fabric.js — full image editor, heavy
- D) annotorious — purpose-built image annotation library

---

## Task Queue / Background Jobs

Need async processing for: segmentation, feature extraction, training,
batch uploads.

**[DECISION: Task queue]**

Choices:
- A) **Celery + Redis** — mature Python task queue, scheduling,
  retries, monitoring **(Recommended)**
- B) ARQ (async Redis Queue) — async-native, simpler
- C) Dramatiq — simpler API than Celery
- D) BackgroundTasks (FastAPI built-in) — only for trivial tasks,
  no persistence
- E) Temporal — complex workflows, heavy infrastructure

**[DECISION: Message broker]**

Choices:
- A) **Redis** — also used as cache, simple setup **(Recommended)**
- B) RabbitMQ — more robust, more operations overhead
- C) PostgreSQL (SKIP LOCKED) — no extra service, limited throughput

---

## Authentication

**[DECISION: Auth strategy]**

Choices:
- A) **JWT (access + refresh tokens)** — stateless, simple, good for
  SPA + API **(Recommended)**
- B) OAuth2 with third-party providers (Google, GitHub) — no password
  management, but external dependency
- C) Session-based (cookie) — traditional, CSRF concerns with SPA

**[DECISION: Auth library]**

Choices:
- A) **python-jose + passlib** — lightweight, manual JWT + hashing
  **(Recommended)**
- B) FastAPI Users — pre-built auth routes, user management, heavier
- C) Auth0 / Clerk — managed auth, external dependency

---

## Deployment

**[DECISION: Deployment target]**

Choices:
- A) **Docker Compose** (single VM) — simple, self-contained
  **(Recommended for MVP)**
- B) Vast.ai GPU instance — GPU for training, not for API serving
- C) Kubernetes — scalable, heavy for MVP
- D) Fly.io / Railway / Render — managed, less control

**[DECISION: CI/CD]**

Choices:
- A) **GitHub Actions** — already in use, free for public repos
  **(Recommended)**
- B) GitLab CI — if repo moves to GitLab
- C) Jenkins — self-hosted, more control

---

## Summary: Recommended Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI (already in use) |
| Database | PostgreSQL + SQLAlchemy 2.0 async + Alembic |
| Vector DB | Qdrant (already in use, Docker Compose) |
| File Storage | Local filesystem (S3 later) |
| Image Processing | OpenCV + NumPy |
| Frontend | React 19 + Vite + shadcn/ui + Tailwind v4 (already in use) |
| Routing | React Router v7 |
| Data Fetching | TanStack Query |
| Forms | React Hook Form + Zod |
| Charts | Recharts + D3.js |
| File Upload | react-dropzone |
| Bbox Annotation | Custom canvas/SVG |
| Task Queue | Celery + Redis |
| Auth | JWT + python-jose + passlib |
| Deployment | Docker Compose |
| CI/CD | GitHub Actions |

Vote on each [DECISION] above before proceeding.
