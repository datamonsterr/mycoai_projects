# Dataset Ingestion Pipeline

## Overview

Ingest messy fungal image datasets into the MycoAI backend (PostgreSQL + Qdrant).
Pipeline: scan → parse → restructure → register species/media → segment → index.

## Prerequisites

- Backend running: `docker compose up -d backend`
- PostgreSQL: `docker compose up -d postgres`
- Owner account created: `docker compose run --rm backend python -m mycoai_retrieval_backend.create_owner --email YOUR_EMAIL --password YOUR_PASSWORD`

## Quick Start

### 1. Scan a messy dataset

```bash
uv --directory research run python -m src.utils.dataset_ingestion.scanner \
  Dataset/new_data \
  /tmp/opencode/manifest.json
```

Output: JSON manifest with species list, media list, image entries.

### 2. Import using the backend batch API

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"owner@test.dev","password":"password123"}' \
  | python3 -c "import json,sys;print(json.load(sys.stdin)['access_token'])")

# Import a directory
curl -s -X POST http://localhost:8000/api/v1/images/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_dir": "/path/to/images", "method": "kmeans"}'
```

Response:
```json
{
  "status": "completed",
  "total": 50,
  "successful": 48,
  "failed": 2,
  "results": [
    {"image_id": "uuid", "strain": "CBS 123", "media": "MEA", "species": "formosanum", "segments": 3}
  ],
  "errors": [
    {"file": "bad.jpg", "error": "reason"}
  ]
}
```

### 3. Index to Qdrant

```bash
curl -s -X POST http://localhost:8000/api/v1/index/reindex \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scope": "all"}'
```

### 4. Verify

```bash
# Count species
curl -s http://localhost:8000/api/v1/species -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Species: {d[\"total\"]}')"

# Count media
curl -s http://localhost:8000/api/v1/media -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Media: {d[\"total\"]}')"
```

## Input Format (Messy Data)

The pipeline handles these filename patterns:

| Pattern | Example | Parsed |
|---------|---------|--------|
| `species CBS 123 MEAo.jpg` | `formosanum CBS 101028 CYAo.jpg` | species=formosanum, strain=CBS 101028, media=CYA, angle=ob |
| `species IBT 456 MEAr.jpg` | `nordicum IBT 5105 MEAr.jpg` | species=nordicum, strain=IBT 5105, media=MEA, angle=rev |
| `T491 MEDIA ANGLE.ext` | `T491 MEA rev.JPG` | strain=T491, media=MEA, angle=rev |
| Folder: `{alpha}/{species}/{strain}/{files}` | `D - L/formosanum/CBS 101028/*.jpg` | species from folder, strain from filename |

## Folder Structure (Well-Formatted Output)

The backend creates this structure per image:

```
Dataset/uploads/{strain}/{media}/{image_id}/
+-- source.jpg           # Original uploaded image
+-- prepared.jpg         # 256x256 preprocessed
+-- bbox_kmeans.jpg      # Bbox overlay visualization
+-- pipeline_kmeans.jpg  # 3-panel visualization (source|prep|bbox)
+-- segments/
    +-- segment_0.jpg    # Cropped colony segment
    +-- segment_1.jpg
    +-- segment_2.jpg
```

## Metadata Management via API

### Create species
```bash
curl -X POST http://localhost:8000/api/v1/species \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Penicillium commune","description":"Common indoor mold"}'
```

### Create media
```bash
curl -X POST http://localhost:8000/api/v1/media \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"MEA","description":"Malt Extract Agar"}'
```

### Update species
```bash
curl -X PATCH http://localhost:8000/api/v1/species/{species_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Penicillium commune (corrected)"}'
```

### Archive species/media
```bash
curl -X DELETE http://localhost:8000/api/v1/species/{species_id} \
  -H "Authorization: Bearer $TOKEN"
```

## Agent Instructions

To restructure an existing dataset and import it:

1. Run `docker compose up -d postgres backend` to ensure services are running
2. Copy dataset into the backend container: `docker cp /path/to/dataset mycoai-backend:/tmp/import_data`
3. Call `POST /api/v1/images/batch` with `{"source_dir": "/tmp/import_data", "method": "kmeans"}`
4. Check the response for success/failure counts
5. If failures exist, check individual `errors` array entries
6. Call `POST /api/v1/index/reindex` to push segments to Qdrant
7. Verify via `GET /api/v1/species`, `GET /api/v1/strains`

## Python API Client

Use `src.utils.dataset_ingestion.ingester.BackendAPIClient`:

```python
from src.utils.dataset_ingestion.ingester import BackendAPIClient, DatasetIngester
from src.utils.dataset_ingestion.scanner import scan_dataset

# Scan
manifest = scan_dataset("Dataset/new_data")
manifest.save(Path("/tmp/manifest.json"))

# Ingest via API
client = BackendAPIClient(base_url="http://localhost:8000/api/v1")
ingester = DatasetIngester(client)
result = ingester.ingest(manifest)
```
