## Context

The MycoAI backend (FastAPI + SQLAlchemy + Celery) currently stores all uploaded images and their segmentation artifacts on the local filesystem via `Path` and `shutil` operations. The `SegmentationPipeline` in `segmentation.py` writes directly to `upload_root / strain / media / image_id /`. Images are served via FastAPI's `StaticFiles` mount at `/static`. This works in single-container dev but fails in multi-replica deployments and loses data on container recreation without external volume mounts.

The existing Docker Compose cluster already runs Postgres, Redis, two Qdrant instances, backend, celery-worker, and frontend. A new `minio` service slots naturally alongside these.

**Constraints**: Must not break the existing image upload/retrieval API contract. Must preserve local-filesystem mode for dev workflows without Docker. Must reimplement behavior locally per the backend reimplementation rule (no imports from `research/`).

## Goals / Non-Goals

**Goals:**
- Add MinIO as a Docker Compose service with persistent named volume
- Introduce an `ObjectStorage` abstraction with `LocalStorage` and `S3Storage` backends
- Plumb storage backend through `config.py` → `app.py` → `SegmentationPipeline` → routes
- Generate presigned URLs for S3-backed image serving
- Auto-create MinIO bucket on first startup via the minio client or backend init

**Non-Goals:**
- Multi-region or CDN-backed storage (future work)
- Image resizing or transcoding at storage layer (already done in segmentation)
- Changing the database schema or Qdrant indexing
- Migrating existing local files to S3 (one-time manual migration acceptable)
- Frontend changes

## Decisions

### Decision 1: MinIO over SeaweedFS or local-only named volume

**Chosen: MinIO**
- S3 API is the industry standard — trivial to swap to AWS S3, Cloudflare R2, or any S3-compatible service later
- Python SDK (`minio` package) is mature and async-compatible
- Built-in web console (port 9001) for debugging
- Single-binary deployment, minimal resource overhead (~256MB RAM)
- Already used in fungal-cv-qdrant research workflows

**Alternatives considered:**
- SeaweedFS: More powerful but heavier, no built-in S3 web console, overkill for image storage
- Docker named volume only: Still local-only, no multi-replica support, no future cloud migration path

### Decision 2: `minio` Python package over `boto3` + `aiobotocore`

**Chosen: `minio>=7.2`**
- Simpler API for put/get/presigned operations
- Direct presigned URL support without STS complexity
- Lighter dependency footprint than full boto3 stack
- Still produces standard S3-compatible presigned URLs

### Decision 3: Presigned URL redirects over proxy-through-backend

**Chosen: HTTP 307 redirect to presigned URL**
- Zero backend bandwidth cost for image serving
- MinIO/nginx handles large file transfers efficiently
- Presigned URLs expire (configurable, default 1 hour)
- Frontend `<img src>` handles redirects transparently

**Risk**: Presigned URLs leak the internal MinIO hostname if not configured correctly. Mitigation: Use `MYCOAI_BACKEND_STORAGE_S3_PUBLIC_ENDPOINT` setting for the public-facing endpoint in presigned URLs, separate from the internal Docker network endpoint.

### Decision 4: Storage abstraction via Protocol class

**Chosen: `ObjectStorage` Protocol with `LocalStorage` and `S3Storage` implementations**
- Backend selected at startup via `STORAGE_BACKEND` env var
- `upload_bytes(key: str, data: bytes) -> str` — returns object URL
- `get_url(key: str) -> str` — returns presigned URL (S3) or `/static/` path (local)
- `delete(key: str) -> None`
- `object_exists(key: str) -> bool`

The `SegmentationPipeline` writes to temp files first (as it does today for OpenCV operations), then uploads via `storage.upload_bytes()`. This minimizes changes to the segmentation logic.

### Decision 5: Bucket auto-creation on startup

A `minio/mc` init container or a backend startup hook creates the bucket if it doesn't exist. In dev, the Docker Compose `command` on the minio service handles this. In prod, the backend calls `make_bucket()` on startup.

### Decision 6: Settings structure

```python
class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MYCOAI_BACKEND_STORAGE_")

    backend: Literal["local", "s3"] = "local"
    upload_root: Path = Path("Dataset/uploads")

    # S3 settings
    s3_endpoint: str = "minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "mycoai-images"
    s3_secure: bool = False
    s3_public_endpoint: str = "http://localhost:9000"
    s3_presigned_expiry: int = 3600  # seconds
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Presigned URL hostname mismatch (internal vs public endpoint) | `S3_PUBLIC_ENDPOINT` setting overrides the host in generated URLs; default matches `S3_ENDPOINT` |
| MinIO data loss if volume not backed up | Named Docker volume survives container restarts; document backup strategy separately |
| `minio` package version conflicts with existing deps | Pin `minio>=7.2,<8`; test `uv lock` integration |
| OpenCV operations still need local temp files | Accept: segmentation reads/writes local temp, then uploads to storage. Temp files cleaned after upload. |
| Bucket creation race condition on multi-replica startup | `make_bucket()` with `exist_ok=True` is idempotent; no locking needed |
