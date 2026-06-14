## Why

The backend currently stores uploaded and processed images on the local filesystem under `Dataset/uploads/`, served via `StaticFiles`. This works for single-instance dev but breaks in multi-replica deployments, loses data on container restart without external volumes, and couples storage to the app container's lifecycle. We need a containerized, persistent, S3-compatible object store that integrates naturally with our existing Docker Compose infra (Postgres, Redis, Qdrant, FastAPI).

## What Changes

- Add MinIO as an S3-compatible object storage service in `docker-compose.yml` (and dev override)
- Add a `minio` Python dependency to the backend `pyproject.toml`
- Introduce an `ObjectStorage` abstraction layer in `services/storage.py` with local-filesystem and S3 backends
- Add `MYCOAI_BACKEND_STORAGE_*` settings in `config.py` (backend, bucket, credentials)
- Update `SegmentationPipeline` and image routes to read/write through `ObjectStorage` instead of direct `Path` operations
- Preserve local-filesystem fallback for dev without Docker (storage backend = `local`)
- Expose MinIO console on a dev-only port for manual inspection

## Capabilities

### New Capabilities

- `image-storage`: Object storage for uploaded and processed fungal images via MinIO (S3-compatible), with local-filesystem fallback for development outside Docker Compose.

### Modified Capabilities

_None_ — this is a new infrastructure capability. Existing image upload/retrieval APIs keep the same contract; only the storage backend changes.

## Impact

- `docker-compose.yml`, `docker-compose.dev.yml`: new `minio` service + volume
- `backend/pyproject.toml`: new `minio>=7.2` dependency
- `backend/src/.../config.py`: new `StorageSettings` with backend/endpoint/bucket/credentials
- `backend/src/.../services/storage.py`: rewrite `StorageService` with `ObjectStorage` protocol + `LocalStorage` + `S3Storage`
- `backend/src/.../segmentation.py`: `SegmentationPipeline` calls storage layer instead of direct `Path`/`shutil`
- `backend/src/.../app.py`: init `ObjectStorage` from settings, pass to pipeline
- `backend/src/.../routes.py`: serve images via storage layer (presigned URLs or proxy)
- `backend/Dockerfile`: no changes needed (runtime deps pull via `uv sync`)
- Frontend: no changes (API contract unchanged)
