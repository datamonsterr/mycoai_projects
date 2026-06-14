## 1. Docker Compose — MinIO service

- [ ] 1.1 Add `minio` service with named volume to `docker-compose.yml` (port 9000, console 9001, healthcheck)
- [ ] 1.2 Add `minio` dev overrides (exposed ports, lenient restart) to `docker-compose.dev.yml`
- [ ] 1.3 Add `minio-setup` init container that creates the `mycoai-images` bucket on first start
- [ ] 1.4 Add `MYCOAI_BACKEND_STORAGE_*` env vars to backend and celery-worker services
- [ ] 1.5 Add `backend` depends_on `minio` with `service_healthy` condition
- [ ] 1.6 Add `uploads_data` volume replacement with `minio_data` named volume

## 2. Backend — Dependencies and config

- [ ] 2.1 Add `minio>=7.2,<8` dependency to `pyproject.toml` and run `uv lock`
- [ ] 2.2 Create `StorageSettings` pydantic-settings class in `config.py` with local/S3 fields
- [ ] 2.3 Add `get_storage_settings()` cached factory function
- [ ] 2.4 Update `.env` example or documentation with storage settings

## 3. Backend — ObjectStorage abstraction

- [ ] 3.1 Define `ObjectStorage` Protocol in `services/storage.py` with `upload_bytes`, `get_url`, `delete`, `object_exists`
- [ ] 3.2 Implement `LocalStorage` class wrapping existing `Path`-based writes and `StaticFiles` serving
- [ ] 3.3 Implement `S3Storage` class using `minio.Minio` client with presigned URL generation
- [ ] 3.4 Add `create_storage(settings: StorageSettings) -> ObjectStorage` factory
- [ ] 3.5 Write unit tests for `LocalStorage` (put/get/delete/exists)
- [ ] 3.6 Write unit tests for `S3Storage` with mocked MinIO client

## 4. Backend — Plumb storage into app

- [ ] 4.1 Update `app.py` to create `ObjectStorage` from `StorageSettings` and inject into pipeline and routes
- [ ] 4.2 Update `SegmentationPipeline` to accept `ObjectStorage` and call `storage.upload_bytes()` after writing segment crops to temp
- [ ] 4.3 Update `ImageRecord` to carry object keys (not local paths) when using S3 backend
- [ ] 4.4 Update `routes.py` image-serving endpoints to use `storage.get_url()` and return `RedirectResponse` for S3
- [ ] 4.5 Update `routes.py` `_create_image` DB helper to store S3 object keys in `file_path`/`crop_path`
- [ ] 4.6 Initialize bucket on app startup when `backend=s3` (idempotent `make_bucket`)

## 5. Backend — Celery worker integration

- [ ] 5.1 Verify celery-worker container receives `MYCOAI_BACKEND_STORAGE_*` env vars from docker-compose
- [ ] 5.2 Ensure celery tasks (batch import, feature extraction) can access storage via shared config

## 6. Validation

- [ ] 6.1 Run `ruff check` and `mypy` on changed backend files
- [ ] 6.2 Run `pytest` on backend tests, including new storage tests
- [ ] 6.3 Start full Docker Compose stack (`docker compose up -d`) and verify MinIO health
- [ ] 6.4 Upload an image via `POST /api/v1/images` and verify it lands in MinIO bucket via console (port 9001)
- [ ] 6.5 Request segment crop URL and verify presigned URL redirect works (307 → image bytes)
- [ ] 6.6 Switch to `STORAGE_BACKEND=local` and verify local filesystem path still works
- [ ] 6.7 Run `pnpm --dir frontend build` to confirm frontend builds without changes
