## ADDED Requirements

### Requirement: Object storage backend selection
The system SHALL support a configurable object storage backend via the `MYCOAI_BACKEND_STORAGE_BACKEND` setting. Valid values are `local` (filesystem) and `s3` (MinIO/S3-compatible). When `backend=local`, the system MUST store files under the path specified by `MYCOAI_BACKEND_UPLOAD_ROOT`. When `backend=s3`, the system MUST connect to the endpoint specified by `MYCOAI_BACKEND_STORAGE_S3_ENDPOINT` using the provided access key, secret key, and bucket from settings.

#### Scenario: Storage defaults to local filesystem
- **WHEN** `MYCOAI_BACKEND_STORAGE_BACKEND` is not set
- **THEN** the system SHALL use local filesystem storage at `MYCOAI_BACKEND_UPLOAD_ROOT`

#### Scenario: Explicit S3 backend selection
- **WHEN** `MYCOAI_BACKEND_STORAGE_BACKEND` is set to `s3` and all `MYCOAI_BACKEND_STORAGE_S3_*` settings are configured
- **THEN** the system SHALL connect to the S3-compatible endpoint and use the specified bucket

#### Scenario: Invalid backend value
- **WHEN** `MYCOAI_BACKEND_STORAGE_BACKEND` is set to an unsupported value
- **THEN** the system SHALL raise a startup error with a descriptive message listing valid options

### Requirement: Image upload stores to object storage
The system SHALL persist uploaded source images and all segmentation artifacts (crops, bbox visuals, pipeline composites) to the configured object storage backend instead of directly writing to the local filesystem via `Path`/`shutil`.

#### Scenario: Upload via local backend
- **WHEN** an image is uploaded with `STORAGE_BACKEND=local`
- **THEN** source images, crops, and pipeline artifacts are written to subdirectories under `UPLOAD_ROOT`

#### Scenario: Upload via S3 backend
- **WHEN** an image is uploaded with `STORAGE_BACKEND=s3`
- **THEN** source images, crops, and pipeline artifacts are written as objects in the configured S3 bucket with object keys matching the existing directory structure (`{strain}/{media}/{image_id}/...`)

### Requirement: Image retrieval serves from object storage
The system SHALL serve stored images (source, crops, pipeline visuals) from the configured object storage backend. For the S3 backend, the system MUST generate presigned GET URLs with a configurable expiry (default 1 hour). For the local backend, the system MUST continue serving via `FileResponse` or `StaticFiles`.

#### Scenario: GET source image via S3
- **WHEN** a client requests an image source URL and `STORAGE_BACKEND=s3`
- **THEN** the system SHALL return a redirect (307) to a presigned URL for the S3 object with the configured expiry

#### Scenario: GET segment crop via S3
- **WHEN** a client requests a segment crop URL and `STORAGE_BACKEND=s3`
- **THEN** the system SHALL return a redirect (307) to a presigned URL for the crop object

#### Scenario: GET source image via local
- **WHEN** a client requests an image source URL and `STORAGE_BACKEND=local`
- **THEN** the system SHALL return a `FileResponse` with the local file path

### Requirement: MinaIO service in Docker Compose
The Docker Compose configuration SHALL include a MinIO service with a named volume for persistent object storage. The service MUST expose the S3 API on port 9000 and the web console on port 9001 (dev only). The backend service MUST depend on MinIO with a `service_healthy` condition when `STORAGE_BACKEND=s3`.

#### Scenario: MinaIO starts with Docker Compose
- **WHEN** `docker compose up -d` is run
- **THEN** a MinIO container SHALL start with a persistent named volume and a pre-created bucket matching the backend's bucket setting

#### Scenario: Backend waits for MinIO
- **WHEN** backend is configured with `STORAGE_BACKEND=s3`
- **THEN** the backend container SHALL not start until MinIO passes its health check

### Requirement: API contract unchanged
The existing image upload and retrieval API endpoints SHALL maintain identical request/response schemas regardless of storage backend. Clients MUST NOT require changes when the storage backend switches between `local` and `s3`.

#### Scenario: Upload response shape unchanged
- **WHEN** an image is uploaded with either storage backend
- **THEN** the response SHALL conform to the existing `ImageResponse` model with `image_id`, `source_url`, `segments`, and `segmentation_method`

#### Scenario: Segment crop endpoint unchanged
- **WHEN** a client requests `GET /api/v1/images/{id}/segments/{index}/crop`
- **THEN** the endpoint SHALL return the image bytes with appropriate content type, either directly (local) or via S3 presigned redirect
