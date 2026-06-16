# MycoAI Retrieval Backend — Test Plan

## Test Pyramid Overview

```
         ┌──────┐
         │ E2E  │  ~15 tests — full user journeys with live services
         ├──────┤
         │ INT  │  ~45 tests — cross-component boundaries with real infra
         ├──────┤
         │ UNIT │ ~200+ tests — isolated functions, fast, no external deps
         └──────┘
```

**Principles:**
- Unit tests: mock all external deps (DB, Redis, Qdrant, Celery, filesystem). Use SQLite `:memory:` for ORM-level tests.
- Integration tests: use real PostgreSQL (`mycoai_test`), Redis (DB 1), Qdrant (test collections). Run with `--test-db` marker.
- E2E tests: spin full app with `TestClient`, real DB/Redis/Qdrant, exercise complete user workflows.
- Every test uses dedicated test resources (separate DB, Redis DB, Qdrant collection) — never touch prod data.

---

## 1. Unit Test Plan

### 1.1 Core Module (`core/`)

| File | Tests | Coverage |
|---|---|---|
| `core/security.py` | `hash_token`: happy path, empty string, unicode token<br>`hash_password`: happy path, verify roundtrip<br>`verify_password`: correct password, wrong password, empty strings<br>`create_access_token`: valid payload, verify sub/role/exp/type fields, non-UTC-aware datetime<br>`create_refresh_token`: valid payload, verify type=refresh<br>`decode_access_token`: valid token, expired token, tampered token, wrong algorithm, missing fields<br>`require_role`: owner role passes, user role raises, None role, custom role names | 18 tests |
| `core/exceptions.py` | `AppError`: default status/type/title, custom detail, extra kwargs<br>`NotFoundError`: status=404, title<br>`AuthenticationError`: status=401<br>`AuthorizationError`: status=403<br>`ValidationError`: status=400, errors list, no errors<br>`ConflictError`: status=409 | 10 tests |
| `core/pagination.py` | `PageParams`: defaults (offset=0, limit=50), negative offset rejected, zero limit rejected, limit>200?<br>`PaginatedResponse`: valid items, empty list, total>items edge, offset>total | 8 tests |
| `core/dependencies.py` | `get_current_user`: valid Bearer token, missing header, malformed header (no Bearer), expired token, wrong token type (refresh used as access), inactive user, user not found in DB<br>`require_role`: owner required → owner passes, owner required → user raises, dataowner → owner passes<br>`require_owner`: owner passes, dataowner passes, user raises, admin raises | 14 tests |
| `core/middleware.py` | `RequestIDMiddleware`: generates UUID when header missing, reuses X-Request-ID from header, response includes header<br>`RequestLoggingMiddleware`: logs method/path/status/duration, includes request_id, measured duration>0 | 6 tests |

### 1.2 Configuration (`config.py`)

| Target | Tests |
|---|---|
| `Settings` | defaults from config class, env var override (`MYCOAI_BACKEND_DATABASE_URL`), `.env` file loading, `lru_cache` singleton<br>`get_settings()` returns same instance | 4 tests |
| `QdrantSettings` | defaults, env prefix `MYCOAI_QDRANT_`, url vs host/port precedence, `get_qdrant_settings()` singleton | 4 tests |
| `StorageSettings` | defaults (local backend), s3 backend config, `get_storage_settings()` singleton | 3 tests |

### 1.3 Database Layer (`database.py`)

| Target | Tests |
|---|---|
| `_build_url` | postgresql:// → postgresql+asyncpg://, already has +asyncpg (no double-replace), non-postgres URL unchanged, empty string |
| `_get_engine` | creates engine with correct URL, returns same engine on second call (singleton) |
| `_get_sessionmaker` | creates sessionmaker, returns same on second call |
| `get_db` | yields AsyncSession, session has correct bind, context manager cleanup |
| `Base` | metadata has expected tables |

### 1.4 Models (`models/__init__.py`)

| Model | Tests |
|---|---|
| `User` | create with defaults (id auto-generated, role=user, is_active=True, timestamps), email uniqueness constraint, role literals, relationships loaded |
| `RefreshToken` | create, user back-populates, expires_at enforcement, token_hash uniqueness |
| `Media` | create, name uniqueness, is_archived default false, name length limit |
| `Species` | create, name uniqueness, cascade delete → strains, cascade delete → images |
| `Strain` | create, (name+species_id) uniqueness constraint, foreign key integrity, source field |
| `Image` | create with all FK required, missing FK raises IntegrityError, cascade delete → segments, cascade delete → feedbacks |
| `Segment` | create, (image_id+segment_index) uniqueness, qdrant_point_id nullable, cascade → qdrant_index_state |
| `RetrievalJob` | create, status default=pending, config JSONB roundtrip, input_summary nullable JSONB |
| `RetrievalResult` | create, rank uniqueness per job, score range float, strain_name/species_name not null |
| `RetrievalNeighbor` | create, result back-populates, similarity float |
| `Feedback` | create, source default=retrieval_result, feedback_type literals, status default=pending, submitter+reviewer relationships |
| `TrainingJob` | create, progress JSONB, is_deployed default false, changes_since_last JSONB |
| `AuditLog` | create, BigInteger→Integer on sqlite, ip_address variant, changes JSONB |
| `QdrantIndexState` | create, segment back-populates, is_active default true, dual UUIDs (segment_id + qdrant_point_id) |
| `SystemState` | create, key primary key, value JSONB |
| `InviteToken` | create, token_hash uniqueness, is_used default false, user relationship |

### 1.5 Schemas (`schemas/`)

| Schema Group | Tests |
|---|---|
| **Auth** (`auth.py`) | `RegisterRequest`: valid, email invalid, password<8 chars, name empty, name>255 chars<br>`LoginRequest`: valid, missing email, missing password<br>`TokenResponse`: all fields, token_type default, expires_in positive<br>`UserResponse`: valid, missing fields, role not in literals<br>`RefreshRequest`: valid, empty token rejected<br>`RegisterWithTokenRequest`: valid, missing token rejected |
| **Species** (`species.py`) | `SpeciesCreate`: valid, name empty, name too long<br>`SpeciesUpdate`: partial update (name only), (description only), empty (both None)<br>`SpeciesResponse`: from_attributes=True, all fields |
| **Feedback** (`feedback.py`) | `FeedbackCreate`: valid all fields, minimal (wrong_prediction + description), wrong feedback_type rejected, empty description rejected<br>`FeedbackUpdate`: accepted/rejected/deferred, invalid status rejected<br>`FeedbackBatchRequest`: valid, empty feedback_ids, invalid status |
| **Dashboard** (`dashboard.py`) | `DashboardStats`: all fields positive<br>`SpeciesDistributionItem`: valid<br>`MediaDistributionItem`: valid |
| **Index schemas** (`index.py`) | Reindex trigger request validation |
| **Images schemas** (`images.py`, `media.py`) | All request/response models validation |
| **Retrieval schemas** (`retrieval.py`) | `RetrievalQueryRequest`: valid, invalid k (<1, >100)<br>`RetrievalJobResponse`: valid<br>`RetrievalResultsResponse`: valid |
| **Training schemas** (`training.py`) | `TrainingTriggerRequest`: valid, reason optional<br>`TrainingDeployRequest`: force default |
| **Admin schemas** (`admin.py`) | `AdminUserItem`, `AdminRoleUpdateRequest`: role validation |
| **Generic schemas** (`__init__.py`) | `ImageListItem`, `ImageListResponse`, `ProblemDetails`, `SegmentDetail`, `StrainItem`, `StrainCreateRequest` |

### 1.6 Image Processing (`image_processing.py`)

| Function | Tests |
|---|---|
| `load_image_bytes` | valid color PNG → 3-channel ndarray, valid grayscale PNG → 2-channel ndarray, valid JPEG, valid WebP, invalid bytes → ValueError, empty bytes → cv.error, large image, 1x1 pixel edge, corrupted image data, default grayscale=False |

### 1.7 Image Models (`image_models.py`)

| Model | Tests |
|---|---|
| `BoundingBox` | valid (x=0,y=0,w=100,h=100), negative x rejected, zero w rejected, zero h rejected, negative w |
| `Segment` | valid, negative segment_index rejected |
| `ImageRecord` | valid, empty segments list |
| `ImageResponse` | valid, model_validate roundtrip |
| `SegmentPatch` | valid, negative index rejected |
| `SegmentPatchRequest` | valid, empty segments + empty deleted, large segment list |

### 1.8 Segmentation (`segmentation.py`)

| Class/Function | Tests |
|---|---|
| `ImageStore` | add → get (found), add → get (missing ID), add overwrite, get after clear |
| `SegmentationPipeline._plate_mask` | valid image, 1x1 image, grayscale input, returns uint8, circle radius calculation |
| `SegmentationPipeline._kmeans_bboxes` | image with clear colonies → >=1 bbox, blank image → 0 bboxes, single small dot, very large image, bbox coordinates within image bounds, max 3 bboxes, out_path writes visualization |
| `SegmentationPipeline._contour_bboxes` | image with contours → >=1 bbox, blank image → 0 bboxes, circular objects scored higher, max 3 bboxes |
| `SegmentationPipeline._compose_pipeline` | valid source+prepared+bbox → horizontal stack 256×768, missing bbox file → handles gracefully, missing source → handles gracefully |
| `SegmentationPipeline._write_segment` | valid crop, bbox at origin, bbox out of bounds (clamped), source image missing, crop directory missing |
| `SegmentationPipeline.segment_upload` | valid image with kmeans → returns ImageRecord with segments, contour method, invalid method → ValueError, storage=None (local path), storage=S3 (mock), no colonies found → 0 segments, source_path doesn't exist |
| `SegmentationPipeline.update_segments` | delete one segment, add new segment, modify existing bbox, delete all segments, patch with no changes |

### 1.9 Storage Service (`services/storage.py`)

| Class | Tests |
|---|---|
| `LocalStorage` | `upload_bytes`: creates file, returns /static/ path, nested key creates dirs, overwrite existing<br>`get_url`: returns /static/ path<br>`get_bytes`: existing file, missing file → None, empty file<br>`delete`: existing file, missing file (no error)<br>`object_exists`: existing → True, missing → False |
| `S3Storage` (mocked Minio) | `ensure_bucket`: creates if not exists, skips if exists<br>`upload_bytes`: calls put_object, returns s3:// URI<br>`get_url`: calls presigned_get_object<br>`get_bytes`: existing object, missing → None, connection error → None<br>`delete`: calls remove_object<br>`object_exists`: existing → True, missing → False, error → False |
| `create_storage` | backend="local" → LocalStorage, backend="s3" → S3Storage (mocked) |

### 1.10 Memory Stores (`services/stores.py`)

| Function | Tests |
|---|---|
| `MemoryStore` | list empty, list after puts, get existing, get missing, put (returns item), put overwrite, remove existing (returns item), remove missing (returns None), concurrent access |
| `seed_data` | first call populates users (5), species (1), strain (1), image (1), second call idempotent, verify owner user has role=owner |
| `find_user_by_email` | existing email → dict, missing email → None, case sensitivity |
| `create_refresh_token_record` | creates record with all fields, token_hash stored correctly |
| `revoke_refresh_token` | existing token removed, non-existing no error, partial match not removed |
| `is_first_user` | empty store → True, after seed → False |
| `as_paginated` | offset 0 limit 10, offset 5 limit 3, offset beyond length → empty, negative offset, zero limit, total count correct |

### 1.11 Qdrant Module (`qdrant/`)

| File | Tests |
|---|---|
| `qdrant/filters.py` | `build_filter(None)` → None, `build_filter(FilterSpec())` → None, each field individually (environment, exclude_environment, strain, exclude_strain, angle, specy, parent_id), multiple exclude_ids, combined must+must_not, all fields simultaneously |
| `qdrant/models.py` | `VectorSpec` dataclass, `NeighborResult` defaults, `FilterSpec` all fields None, `QueryByImageRequest` validation (k min/max), `QueryByIdRequest` validation, `PointUpsertRequest` empty vectors, `QueryResult` empty neighbors, `AggregationResult` ranking order, `CollectionStats` defaults |
| `qdrant/aggregation.py` | weighted strategy: correct top_species, uni strategy: vote-based, empty neighbors → unknown, unknown specy→strain lookup, total_neighbors=0 edge, single neighbor, tied scores, manual_weighted strategy with weights, strategy fallback |
| `qdrant/collections.py` | `collection_exists`: True, False, empty list<br>`get_collection_stats`: points_count, vector_types extraction, empty collection, no vectors<br>`list_environments`: multiple, duplicates deduplicated, empty collection |
| `qdrant/operations.py` | `query_points_by_image`: with filter, without filter, custom collection<br>`query_points_by_id`: point found, point not found → ValueError, exclude_self, exclude_siblings, missing vector name<br>`upsert_points`: valid batch, empty batch → 0<br>`delete_points`: valid ids, empty list → 0 |
| `qdrant/client.py` | `init_qdrant_client`: url mode, host/port mode, thread safety, singleton<br>`get_qdrant_client`: returns existing, initializes if None<br>`get_collection_name`: lru_cache |

### 1.12 Qdrant Client Service (`services/qdrant_client.py`)

| Method | Tests |
|---|---|
| `QdrantClientService.__init__` | creates QdrantClient with settings, correct collection name |
| `upsert_point` | valid point with named vectors, point with single vector, point with empty payload |
| `query` | results returned, limit enforcement, custom vector_name, empty results |

### 1.13 Feature Extraction (`services/feature_extraction.py`)

| Function | Tests |
|---|---|
| `extract_features` | valid image → returns all vector keys, valid image → correct dimensions per VECTOR_DIMS, colorhistogram normalizes to 1, colorhistogramhs uses HSV, gabor returns 32 floats, non-existent file → zero vectors, corrupted image → zero vectors, no OpenCV (mock ImportError) → zero vectors, VECTOR_DIMS completeness check |
| `_rgb_histogram` | uniform image → flat histogram, all-black image, all-white image |
| `_hs_histogram` | red image → hue distribution, grayscale → saturation near 0 |
| `_gabor_features` | returns 32 values, different orientations produce different values |
| `_zero_vectors` | all keys present, dimensions match VECTOR_DIMS, all values 0.0 |

### 1.14 Batch Import Metadata Parser (`tasks/batch.py` helpers)

| Function | Tests |
|---|---|
| `_is_artifact_filename` | segment_0.jpg → True, source.jpg → True, prepared.jpg → True, bbox_kmeans.jpg → True, pipeline_kmeans.jpg → True, DTO_148-C8_CYAob.jpg → False, normal file.jpg → False, uppercase SEGMENT_1.PNG → True, non-image extension still matches pattern |
| `_is_artifact_species` | "unknown" → True, "img1" → True, "source" → True, "Penicillium commune" → False, "segment_0" → True, "seg_42" → True, "pipeline_test" → True, "bbox_something" → True, "test-kmeans" → True, "test-kmeans" actually falls through, "DSCN1234" → True, "img 5" → True, "t42" → True, "T(15)" → True, "DTO 148-C8" → True, "CBS 170.87 embedded" → True, "Aspergillus niger" → False |
| `_normalize_angle` | "o" → "ob", "r" → "rev", "ob" → "ob", "rev" → "rev", "unknown" → "unknown", "OB" (case insensitive) → "ob" |
| `_parse_filename_metadata` | DTO format: "DTO 148-C8 CYAob_edited.jpg" → strain=DTO 148-C8, media=CYA, angle=ob<br>CBS format: "Penicillium commune CBS 123.45 MEAo.jpg" → species, strain, media, angle<br>T-number: "T491 MEA rev.JPG" → strain=T491, media=MEA, angle=rev<br>CYA30→CYA normalization<br>folder path fallback: "UnkSpec/DTO 148-C8/file.jpg" → species from folder<br>no strain code: "Some Species Name MEA ob.jpg" → species, strain=unknown<br>only filename, no metadata: "image.jpg" → all unknown<br>empty filename, empty rel_path<br>unicode characters in species name |

### 1.15 Celery App (`celery_app.py`)

| Target | Tests |
|---|---|
| `create_celery_app` | returns Celery instance, broker URL from settings, result backend from settings, app name correct |

### 1.16 Qdrant Client Factory (`qdrant_client.py`)

| Target | Tests |
|---|---|
| `create_qdrant_client` | returns AsyncQdrantClient with correct host/port, api_key empty → None passed |

### 1.17 Repos (`repos/`)

| Repo | Tests |
|---|---|
| `UserRepository` | `get_user`: existing, non-existing UUID, invalid UUID string<br>`list_users`: all, filtered by role, filtered by is_active, offset/limit, empty result<br>`count_users`: unfiltered, role filter, is_active filter<br>`count_active_owners`: owners only, includes dataowner<br>`update_user_role`: valid role change, user not found<br>`update_user_status`: activate, deactivate, user not found |
| `Media` (repo) | `create_media`: valid, duplicate name → ConflictError<br>`get_media`: existing, non-existing<br>`list_media`: active only, archived, offset/limit<br>`count_media`: empty, after insert<br>`update_media`: rename, update description, rename to existing name → ConflictError, non-existing → NotFoundError<br>`archive_media`: active → archived, non-existing → NotFoundError<br>`restore_media`: archived → active, already active, non-existing → NotFoundError |

### 1.18 Tasks (`tasks/`)

| Task | Tests |
|---|---|
| `tasks/segmentation.py::run` | valid image_id with source → returns completed, missing image_id → error dict, missing source file → error dict, kmeans method, contour method, archived old segments, data_update_status set to "updated_requires_reindex" |
| `tasks/feature_extraction.py::run` | valid segment_id → indexed, missing segment_id → error, missing crop file → error, extract_features returns empty → error, qdrant point_id assigned, QdrantIndexState created |
| `tasks/training.py::run` | returns queued status with job_id |

### 1.19 App Factory (`app.py`)

| Target | Tests |
|---|---|
| `create_app` | returns FastAPI instance, health endpoint returns 200, root endpoint returns docs/health URLs, CORS middleware present, RequestIDMiddleware present, RequestLoggingMiddleware present, static files mounted, all routers included, AppError handler returns ProblemDetails JSON, StarletteHTTPException handler returns ProblemDetails JSON, 404 returns ProblemDetails with title "Not Found" |

### 1.20 Services — Retrieval (`services/retrieval.py`)

| Function | Tests |
|---|---|
| `retrieve` | valid query → empty list (stub), non-empty query, limit respected |

---

## 2. Integration Test Plan

### 2.1 PostgreSQL Integration (`tests/integration/test_integration_postgres.py`)

**Resources:** `mycoai_test` database, created/dropped per test function.

| Test | Description |
|---|---|
| Connection ping | AsyncEngine connects, executes SELECT 1 |
| Create + query User | Insert user, query by email, verify all fields |
| Create Species + Strain with relations | Insert species → insert strain with FK → verify relationship loaded |
| Transaction rollback | Insert → no commit → verify not persisted |
| Media unique constraint | Insert duplicate name → IntegrityError |
| Image FK integrity | Insert Image with non-existent strain_id → IntegrityError |
| AuditLog insert + query | Full cycle: User → AuditLog → verify JSONB changes |
| Concurrent sessions | Insert 2 species in same session → verify both persisted |
| **NEW: RetrievalJob + Results cascade** | Create job → add results → verify cascade delete |
| **NEW: QdrantIndexState FK chain** | Segment → QdrantIndexState → verify relationship |
| **NEW: Feedback submitter+reviewer** | Create feedback with submitter → add reviewer → verify both relationships |
| **NEW: TrainingJob progress JSONB** | Insert JSONB progress → query → verify deserialization |
| **NEW: SystemState upsert** | Insert key/value → update value → verify overwrite |
| **NEW: InviteToken lifecycle** | Create → mark used → verify token_hash uniqueness |
| **NEW: Batch insert performance** | Insert 100 Users → verify all persisted |
| **NEW: Nullable fields roundtrip** | Image with null angle, null prepared_path → verify |
| **NEW: DateTime timezone** | Insert with tz → query → verify tz preserved |

### 2.2 Redis Integration (`tests/integration/test_integration_redis.py`)

**Resources:** Redis DB 1 (`redis://localhost:6379/1`), keys prefixed `test:`.

| Test | Description |
|---|---|
| Connection ping | PING → True |
| Set + Get | SET key → GET key → assert value |
| SETEX with TTL | SETEX → GET → assert TTL > 0 |
| Delete key | SET → DEL → GET → None |
| Cache pattern | SET with JSON → GET → json.loads → verify |
| PubSub | SUBSCRIBE → PUBLISH → receive message |
| **NEW: Increment counter** | INCR → verify atomic increment |
| **NEW: List push/pop** | LPUSH → RPOP → verify FIFO |
| **NEW: Hash operations** | HSET → HGET → HGETALL |
| **NEW: Set operations** | SADD → SMEMBERS → SISMEMBER |
| **NEW: Expire key** | SET → EXPIRE → wait → GET → None |
| **NEW: Pipeline batch** | Pipeline SET multiple → execute → GET all |
| **NEW: Celery broker pattern** | Simulate Celery message push/pop |

### 2.3 Qdrant Integration (`tests/integration/test_integration_qdrant.py`)

**Resources:** Test collection `test_integration_points` (created per test, cleaned up after).

| Test | Description |
|---|---|
| Connection health | health_check() returns non-None |
| Collection exists | get_collections → verify named collection present |
| Get collection info | vector size > 0 |
| Upsert + Search | Create collection → upsert point → query_points → verify match |
| Filtered search | Upsert 2 points with different environments → filter by environment → verify |
| Batch upsert | Upsert 5 points → verify count |
| **NEW: Reindex trigger flow** | Create segment → index to Qdrant → verify QdrantIndexState → delete segment → reindex → verify new point_id |
| **NEW: Delete points** | Upsert → delete by id → verify count reduced |
| **NEW: Collection lifecycle** | Create test collection → upsert data → verify stats → delete collection |
| **NEW: Vector search with filter** | Explicit filter_spec → build_filter → query → verify results obey filter |
| **NEW: Multiple named vectors** | Upsert with 2 vector types → query by each → verify both work |
| **NEW: Scroll pagination** | Upsert 10 points → scroll limit=3 → verify offset-based pagination |
| **NEW: Payload field retrieval** | Upsert with payload → retrieve by id → verify all payload fields |
| **NEW: Empty collection search** | Query empty collection → empty results, no error |

### 2.4 Celery Integration (`tests/integration/test_integration_celery.py`) **[NEW]**

**Resources:** Redis DB 1 as broker, dedicated test queue.

| Test | Description |
|---|---|
| App creation | create_celery_app returns Celery instance with correct broker |
| Task registration | Verify tasks/ modules auto-discovered |
| Task dispatch | Send task → verify received in queue |
| Task result backend | Dispatch → wait for result → AsyncResult.get() |
| **NEW: Segmentation task via Celery** | Dispatch segmentation.run(image_id) → verify status updated |
| **NEW: Feature extraction task** | Dispatch feature_extraction.run(segment_id) → verify point indexed |
| **NEW: Training task** | Dispatch training.run(job_id) → verify queued status |
| **NEW: Task retry on failure** | Simulate Qdrant down → verify retry with exponential backoff |
| **NEW: Task timeout** | Long-running task → verify timeout handling |

### 2.5 API Integration (`tests/integration/test_integration_api.py`)

| Test | Description |
|---|---|
| Register → Login → Refresh → Logout flow | Full auth cycle with real DB |
| Full retrieval flow (mocked Qdrant) | POST retrieval/query → GET jobs/{id} → verify status |
| Species CRUD full cycle | POST → GET → PATCH → DELETE with real DB |
| Media CRUD via ORM | Create → Update → Archive cycles |
| Feedback submit → review cycle | Create species/strain/media/image → create job+result → submit feedback → review |
| RBAC enforcement | User role tries POST species → 403 |
| **NEW: Image upload → segment → persist** | Upload image → verify segments in DB |
| **NEW: Batch import from directory** | POST /batch with source_dir → verify images persisted |
| **NEW: Batch ZIP upload** | POST /batch-zip with ZIP file → verify extracted+segmented+persisted |
| **NEW: Image list with filters** | GET /images?species_id=X → verify filter works |
| **NEW: Dashboard stats** | GET /dashboard/stats → verify counts match DB |
| **NEW: Strains CRUD** | Full cycle: create → list → get → archive |
| **NEW: Training trigger** | POST /training/trigger → verify job created |
| **NEW: Admin endpoints** | GET /admin/users → list, PATCH role → verify change |
| **NEW: Index reindex endpoint** | POST /index/reindex → verify reindex triggered |

### 2.6 Storage Integration (`tests/integration/test_integration_storage.py`) **[NEW]**

| Test | Description |
|---|---|
| LocalStorage file lifecycle | upload_bytes → get_bytes → delete → object_exists |
| LocalStorage nested paths | key="a/b/c.jpg" → creates directories |
| LocalStorage large file | Upload 10MB file → verify integrity |
| S3Storage mock | Upload → presigned URL → download → delete |

---

## 3. E2E Test Plan

### 3.1 Full Image Pipeline E2E **[NEW]**

**Resources:** Dedicated `mycoai_e2e` database, Redis DB 2, Qdrant collection `test_e2e_pipeline`.

| Test | Steps |
|---|---|
| Single image upload → segment → retrieve | 1. Register user → login → get token<br>2. POST /api/v1/images with test image, strain=A, media=MEA<br>3. Verify 201 → image_id returned, segments>0<br>4. POST /api/v1/retrieval/query with image_id<br>5. Poll GET /api/v1/retrieval/jobs/{job_id} until completed<br>6. Verify rankings returned with species scores |
| Batch folder import → index → search | 1. Create test directory with 3 images<br>2. POST /api/v1/images/batch with source_dir<br>3. Verify all 3 images persisted<br>4. Verify segments created for each<br>5. POST /api/v1/index/reindex to trigger Qdrant indexing<br>6. Poll until indexing complete<br>7. Search by image → verify neighbors found |
| Batch ZIP upload → full pipeline | 1. Create ZIP with 2 images in folder structure<br>2. POST /api/v1/images/batch-zip with ZIP file<br>3. Verify extraction → segmentation → DB persist<br>4. Verify segments indexed in Qdrant |
| Species → strain → image → segment hierarchy | 1. Create species "Test Species"<br>2. Create strain "TS-001" linked to species<br>3. Upload image linked to strain<br>4. Verify image.species_id matches strain.species_id<br>5. Archive strain → verify images still accessible |
| Re-segmentation triggers reindex | 1. Upload image with kmeans → index<br>2. Re-segment with contour → verify old segments archived<br>3. Verify QdrantIndexState updated<br>4. Query → verify new vectors used |

### 3.2 Auth E2E

| Test | Steps |
|---|---|
| Register → Login → Access protected route → Refresh → Logout | Full flow, verify token expiration, verify refresh works, verify logout invalidates refresh token |
| Invite token flow | Owner creates invite → invited user registers with token → verify role assigned |
| Session persistence | Login → access multiple endpoints → verify same user context |
| Concurrent sessions | Login from two "devices" → logout one → verify other still valid |

### 3.3 RBAC E2E

| Test | Steps |
|---|---|
| User cannot access owner endpoints | Login as user → attempt POST /species → 403<br>→ attempt POST /images/batch → 403<br>→ attempt PATCH segments → 403<br>→ attempt POST /admin/* → 403 |
| Owner can access all | Login as owner → all CRUD operations succeed |
| Dataowner has same permissions as owner | Login as dataowner → verify owner-level access |

### 3.4 Error Handling E2E

| Test | Steps |
|---|---|
| 404 on missing resource | GET /api/v1/species/nonexistent-uuid → ProblemDetails JSON |
| 401 on missing auth | GET /api/v1/images without token → 401 |
| 403 on wrong role | User tries owner action → 403 |
| 409 on duplicate | POST species with existing name → 409 ConflictError |
| 422 on invalid input | POST species with empty name → 422 |
| 422 on invalid method | POST image with method=invalid → 422 |
| 500 on internal error | Simulate DB connection failure → ProblemDetails JSON |

---

## 4. Test Infrastructure

### 4.1 Environment Variables

```bash
# For integration tests
MYCOAI_TEST_DB_URL=postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai_test
MYCOAI_TEST_REDIS_URL=redis://localhost:6379/1
MYCOAI_TEST_QDRANT_HOST=localhost
MYCOAI_TEST_QDRANT_PORT=6333

# For E2E tests
MYCOAI_E2E_DB_URL=postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai_e2e
MYCOAI_E2E_REDIS_URL=redis://localhost:6379/2
```

### 4.2 Database Setup

```sql
-- Run once before tests
CREATE DATABASE mycoai_test OWNER mycoai;
CREATE DATABASE mycoai_e2e OWNER mycoai;

-- Tests auto-create/drop tables per function (integration) or per session (E2E)
```

### 4.3 Redis Setup

- Integration tests use DB 1 (flush per test via key prefix `test:`)
- E2E tests use DB 2 (flush per test session)
- Celery broker uses DB 1 for integration tests

### 4.4 Qdrant Setup

- Integration tests create `test_integration_*` collections per test, delete after
- E2E tests create `test_e2e_*` collections per test session

### 4.5 Test Configuration Updates (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
    "integration_postgres: requires PostgreSQL connection",
    "integration_redis: requires Redis connection",
    "integration_qdrant: requires Qdrant connection",
    "integration_celery: requires Celery/Redis broker",
    "integration_storage: requires storage backend",
    "e2e: end-to-end tests requiring full infrastructure",
    "slow: tests that take >1s",
    "unit: fast unit tests with no external deps",
]

[tool.coverage.run]
source = ["src/mycoai_retrieval_backend"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

### 4.6 Factory Fixtures (`tests/factories.py`) **[NEW]**

```python
# Test data factories to reduce boilerplate
- UserFactory: create user with defaults
- SpeciesFactory: create species
- StrainFactory: create strain linked to species
- MediaFactory: create media
- ImageFactory: create image with all FKs
- SegmentFactory: create segment linked to image
- RetrievalJobFactory: create job
- RetrievalResultFactory: create result linked to job
```

### 4.7 Test Conftest Updates

```
tests/conftest.py          # Unit test fixtures (SQLite :memory:, TestClient)
tests/integration/conftest.py  # Integration fixtures (real Postgres, Redis, Qdrant)
tests/e2e/conftest.py      # E2E fixtures (full app with real services)
tests/factories.py          # Shared factory functions
```

---

## 5. Test Execution Commands

```bash
# Unit tests only (fast, no external deps)
uv --directory backend run pytest tests/ -m "not integration and not e2e" -v

# Unit tests with coverage
uv --directory backend run pytest tests/ -m "not integration and not e2e" --cov -v

# Integration tests (requires Postgres + Redis + Qdrant running)
uv --directory backend run pytest tests/integration/ -v -m "integration"

# Individual integration suites
uv --directory backend run pytest tests/integration/ -m "integration_postgres" -v
uv --directory backend run pytest tests/integration/ -m "integration_redis" -v
uv --directory backend run pytest tests/integration/ -m "integration_qdrant" -v
uv --directory backend run pytest tests/integration/ -m "integration_celery" -v

# E2E tests (requires full infrastructure)
uv --directory backend run pytest tests/e2e/ -v -m "e2e"

# All tests with coverage report
uv --directory backend run pytest tests/ --cov --cov-report=html --cov-report=term -v

# Skip slow tests in CI
uv --directory backend run pytest tests/ -m "not slow and not integration and not e2e" -v

# Run specific test file
uv --directory backend run pytest tests/test_core.py -v
uv --directory backend run pytest tests/integration/test_integration_qdrant.py -v

# Run with verbose output and no capture (for debugging)
uv --directory backend run pytest tests/test_security.py -vvs
```

---

## 6. Coverage Targets

| Layer | Current Estimate | Target |
|---|---|---|
| **Unit** | ~60% | **≥90%** line coverage |
| **Integration** | ~40% | **≥85%** of integration touchpoints covered |
| **E2E** | ~15% | **All critical user journeys** (5 flows) |
| **Overall** | ~50% | **≥80%** |

### Critical gaps to close first:
1. `segmentation.py` — core business logic, currently 0% unit tested
2. `tasks/batch.py` — metadata parser, 0% unit tested
3. `services/feature_extraction.py` — 0% unit tested
4. `core/security.py` — only 2 unit tests (require_role), missing token tests
5. `services/storage.py` — 0% tested
6. `models/__init__.py` — only 3 integration tests, 0 unit tests on model constraints
7. `repos/` — partially tested via integration, 0 isolated unit tests
8. Celery integration — 0 tests

---

## 7. Implementation Order

### Phase 1: Foundation (Unit Tests)
1. `core/exceptions.py` — 10 tests
2. `core/security.py` — 18 tests
3. `core/pagination.py` — 8 tests
4. `config.py` — 11 tests (Settings + QdrantSettings + StorageSettings)
5. `image_processing.py` — 6 tests (already partially done)
6. `image_models.py` — 10 tests
7. `services/stores.py` — 15 tests
8. `schemas/` — 40+ tests across all schema files

### Phase 2: Business Logic (Unit Tests)
9. `segmentation.py` — 25 tests
10. `services/storage.py` — 20 tests
11. `services/feature_extraction.py` — 15 tests
12. `tasks/batch.py` (parser helpers) — 30 tests
13. `qdrant/filters.py` — 15 tests
14. `qdrant/aggregation.py` — 12 tests
15. `qdrant/models.py` — 10 tests
16. `qdrant/collections.py` — 8 tests
17. `qdrant/operations.py` — 12 tests

### Phase 3: Data Layer (Unit + Integration)
18. `models/__init__.py` — 25 unit tests (model validation)
19. `repos/user.py` — 12 tests
20. `repos/media.py` — 12 tests
21. Integration: PostgreSQL — extend from 7 → 18 tests
22. Integration: Redis — extend from 5 → 13 tests
23. Integration: Qdrant — extend from 5 → 14 tests
24. Integration: Celery — NEW, 10 tests

### Phase 4: API & E2E
25. `core/dependencies.py` — 14 tests
26. `core/middleware.py` — 6 tests
27. Integration: API — extend from 6 → 15 tests
28. E2E: Image pipeline — 5 tests
29. E2E: Auth — 4 tests
30. E2E: RBAC — 3 tests
31. E2E: Error handling — 7 tests

---

## 8. Test Naming Convention

```
test_{function_name}_{scenario}_{expected_behavior}

Examples:
test_hash_password_roundtrip_verify_succeeds
test_load_image_bytes_invalid_data_raises_ValueError
test_build_filter_none_returns_None
test_create_media_duplicate_name_raises_ConflictError
test_segment_upload_invalid_method_raises_ValueError
```

Pattern: `test_<what>_<condition>_<expected>`
