# Technical Spec: Backend Architecture

## Overview

Design the FastAPI backend project structure, service layer, middleware,
and dependency injection patterns.

---

## Project Structure

**[DECISION: Backend package layout]**

Choices:
- A) **Domain-based**: `src/mycoai_retrieval_backend/{api,core,models,
  schemas,services,repos}/` with API routers grouped by domain
  (images, retrieval, species, feedback, training, auth)
  **(Recommended)**
- B) Feature-based: `src/mycoai_retrieval_backend/features/{images,
  retrieval,...}/` each with own router, service, model, schema
- C) Flat: all files in one package (current state — not scalable)

**Recommended structure (Option A):**

    src/mycoai_retrieval_backend/
    +-- api/                    # FastAPI routers
    |   +-- router.py           # Master router aggregating all sub-routers
    |   +-- images.py           # POST /api/images/upload, batch
    |   +-- retrieval.py        # POST /api/retrieval/query
    |   +-- species.py          # CRUD /api/species
    |   +-- feedback.py         # POST /api/feedback, GET /api/feedback/inbox
    |   +-- training.py         # POST /api/training/trigger, GET status
    |   +-- auth.py             # POST /api/auth/login, register
    |   +-- dashboard.py        # GET /api/dashboard/stats, charts
    +-- core/
    |   +-- config.py           # Pydantic settings (already exists)
    |   +-- security.py         # JWT, password hashing, role checks
    |   +-- dependencies.py     # FastAPI Depends() callables
    |   +-- exceptions.py       # Custom exception classes + handlers
    +-- models/
    |   +-- base.py             # SQLAlchemy declarative base
    |   +-- user.py             # User, Role models
    |   +-- species.py          # Species model
    |   +-- strain.py           # Strain model
    |   +-- image.py            # Image model
    |   +-- feedback.py         # Feedback model
    |   +-- training_job.py     # TrainingJob model
    +-- schemas/
    |   +-- images.py           # Pydantic request/response models
    |   +-- retrieval.py
    |   +-- species.py
    |   +-- feedback.py
    |   +-- training.py
    |   +-- auth.py
    |   +-- dashboard.py
    +-- services/
    |   +-- segmentation.py     # Call fungal-cv-qdrant segmentation
    |   +-- feature_extraction.py # Call feature extractors
    |   +-- qdrant_client.py    # Qdrant query, upsert, delete
    |   +-- retrieval.py        # Orchestrate: extract -> query -> aggregate
    |   +-- training.py         # Trigger + monitor training jobs
    |   +-- batch.py            # Batch upload processing
    |   +-- storage.py          # File read/write, S3 abstraction
    +-- repos/
    |   +-- species.py          # Database queries (SQLAlchemy)
    |   +-- strain.py
    |   +-- image.py
    |   +-- feedback.py
    |   +-- user.py
    +-- tasks/                  # Celery tasks
    |   +-- segmentation.py
    |   +-- feature_extraction.py
    |   +-- training.py
    |   +-- batch.py
    +-- app.py                  # create_app() factory
    +-- main.py                 # Entrypoint
    +-- __init__.py

---

## Middleware

**[DECISION: Middleware stack]**

Select all that apply:

- [ ] A) **CORS** — required for browser access from frontend
  **(Recommended)**
- [ ] B) **Request ID** — UUID per request, in headers + logs
  **(Recommended)**
- [ ] C) **Request logging** — method, path, status, duration
  **(Recommended)**
- [ ] D) Rate limiting — per-IP or per-user throttling
- [ ] E) Compression (GZip) — for large JSON responses
- [ ] F) Trusted host — restrict Host header

---

## Dependency Injection

**[DECISION: How to inject DB session]**

Choices:
- A) **FastAPI Depends + yield** — `get_db()` dependency yields
  async session, auto-close on response **(Recommended)**
- B) Context manager in each service — manual session management
- C) Global session pool — simpler, risk of leaks

**[DECISION: How to inject current user]**

Choices:
- A) **Depends(get_current_user)** — decodes JWT, fetches user,
  returns User model **(Recommended)**
- B) Depends(get_current_user_id) — only returns UUID, lighter
- C) Attach to request.state — implicit, less explicit

---

## Error Handling

**[DECISION: Error response format]**

Choices:
- A) **RFC 7807 Problem Details** — `{"type":"...","title":"...",
  "status":400,"detail":"...","instance":"..."}`
  **(Recommended)**
- B) Simple JSON: `{"error":"message"}`
- C) Structured: `{"error":{"code":"RESOURCE_NOT_FOUND","message":"..."}}`

---

## API Versioning

**[DECISION: API versioning strategy]**

Choices:
- A) **URL prefix**: `/api/v1/images/` — explicit, easy to route
  **(Recommended)**
- B) Header-based: `Accept: application/vnd.mycoai.v1+json`
- C) Query param: `/api/images/?version=1`
- D) No versioning (break things) — fine for internal MVP

---

## Background Tasks

**[DECISION: Sync vs async services]**

Choices:
- A) **Async where possible, sync for CPU-bound ops** — async DB
  queries, sync file I/O in thread pool, Celery for heavy tasks
  **(Recommended)**
- B) All sync — simpler, limits throughput
- C) All async — complex, some libraries (OpenCV) are not async

**[DECISION: How batch uploads work]**

Choices:
- A) **Upload -> return job_id -> Celery processes -> poll status**
  **(Recommended)**
- B) Upload -> synchronous processing -> return results (times out for
  large batches)
- C) WebSocket streaming progress — more complex but real-time

---

## Storage Service

**[DECISION: File storage backend]**

Choices:
- A) **Local filesystem** — `Dataset/uploads/` (configurable via
  `MYCOAI_BACKEND_UPLOAD_ROOT`). Images stored as
  `{strain}/{media}/{image_id}/source.jpg`. Served via FastAPI
  StaticFiles at `/static/`. **(Recommended for dev)**
- B) S3 / MinIO — object storage, pre-signed URLs, cloud-ready
- C) Hybrid — metadata in DB, files on local/S3

**Current implementation:** Local filesystem at `Dataset/uploads/`.
SegmentationPipeline writes artifacts (source, prepared, bbox, pipeline,
segments) into per-image directories. ImageStore keeps in-memory cache
of recent uploads. No S3/MinIO integration exists yet.
