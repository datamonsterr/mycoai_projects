# Technical Spec: Technology Stack

## Overview

Chosen technology stack for backend, frontend, database, vector store,
file storage, and deployment. All decisions resolved per the recommended
options below.

---

## Backend Framework

**[DECISION: Backend framework] ✓ A) FastAPI**
- Async-native, Pydantic integration, auto-docs, good for ML/API workloads.
  Already scaffolded in `backend/`.

---

## Database

**[DECISION: Database engine] ✓ A) PostgreSQL 16**
- Production-grade, supports pgvector extension, full-text search, JSONB,
  concurrent-safe.

**[DECISION: ORM / DB access layer] ✓ A) SQLAlchemy 2.0 (async)**
- Mature ORM, async support via asyncpg, Alembic migrations.

**[DECISION: Migration tool] ✓ A) Alembic**
- Pairs with SQLAlchemy. Auto-generates migrations from model diffs.

---

## Vector Database

**[DECISION: Vector database] ✓ A) Qdrant**
- Already in use by fungal-cv-qdrant experiments. Cosine distance, named
  vectors, rich filtering, Rust-based performance.

**[DECISION: Qdrant deployment mode] ✓ A) Docker Compose**
- Development + small production. Single-node Qdrant container.

---

## File / Image Storage

**[DECISION: File storage] ✓ A) Local filesystem**
- Simple, already the pattern in fungal-cv-qdrant (e.g. Dataset/, weights/).
  Plan: migrate to S3-compatible storage later.

**[DECISION: Image processing pipeline] ✓ A) OpenCV + NumPy**
- Already used by fungal-cv-qdrant experiments. Fast for CV operations.

---

## Frontend Framework

Already scaffolded with React 19 + Vite + shadcn/ui + Tailwind v4.

**[DECISION: Frontend routing] ✓ A) React Router v7**
- Standard SPA routing, config-based route definitions, `createBrowserRouter`.

**[DECISION: Server state / data fetching] ✓ A) TanStack Query (React Query)**
- Caching, retry, background refetch, devtools.

**[DECISION: Form handling] ✓ A) React Hook Form + Zod**
- Performant form state, type-safe Zod validation.

**[DECISION: Charting / Graph visualization] ✓ A) Recharts + D3.js**
- Recharts for pie/bar/line charts. D3.js for KNN graph and custom visuals.

**[DECISION: File upload component] ✓ A) react-dropzone**
- Drag-and-drop, image preview, widely used.

**[DECISION: Image annotation (bounding boxes)] ✓ A) Custom canvas/SVG overlay**
- Lightweight, full control, shadcn/ui-compatible.

---

## Task Queue / Background Jobs

**[DECISION: Task queue] ✓ A) Celery + Redis**
- Mature Python task queue, scheduling, retries, monitoring.

**[DECISION: Message broker] ✓ A) Redis**
- Also used as cache. Simple setup.

---

## Authentication

**[DECISION: Auth strategy] ✓ A) JWT (access + refresh tokens)**
- Stateless, simple, good for SPA + API.

**[DECISION: Auth library] ✓ A) python-jose + passlib**
- Lightweight, manual JWT + bcrypt password hashing.

---

## Deployment

**[DECISION: Deployment target] ✓ A) Docker Compose (single VM)**
- Simple, self-contained. All services in one docker-compose.yml.

**[DECISION: CI/CD] ✓ A) GitHub Actions**
- Already in use, free for public repos.

---

## Summary: Resolved Stack

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
