# DTO Dataset Import Instructions

## Overview

Import `Dataset/original/` (DTO-xxx folders) into the MycoAI backend
(PostgreSQL metadata + Qdrant vector search).

**Pipeline**: scan → register species/media → segment images → upload to DB → index to Qdrant.

## Prerequisites

1. **PostgreSQL** running: `docker compose up -d postgres` (or local)
2. **Backend** running: `docker compose up -d backend` (or `uv run main.py`)
3. **Qdrant** running: `mise run qdrant-up` (or `docker compose up -d qdrant`)
4. **Owner account** created:
   ```bash
   uv run python -m backend.create_owner --email owner@mycoai.dev --password password123
   ```
5. **Python deps** installed: `uv sync --all-groups`

## Dataset Format

The import script expects `Dataset/original/` with this structure:

```
Dataset/original/
├── DTO 148-C8 Penicillium cyclopium/
│   ├── DTO 148-C8 CYAob_edited.jpg
│   ├── DTO 148-C8 CYAob_edited_2.jpg
│   ├── DTO 148-C8 MEAr_edited.jpg
│   └── ...
├── DTO 148-C9 Penicillium polonicum/
│   ├── DTO 148-C9 CYAob_edited.jpg
│   └── ...
└── DTO 148-E6 Penicillium commune/
    └── ...
```

**Folder naming**: `{STRAIN_CODE} {SPECIES_NAME}`
- Strain code: `DTO 148-C8`, `DTO 148-C9`, etc.
- Species: `Penicillium cyclopium`, `Penicillium polonicum`, etc.

**File naming**: `{STRAIN_CODE} {MEDIA}{angle}_edited.jpg`
- Media: `CYA`, `MEA`, `YES`, `DG18`, `CREA`, `OA`, `M40Y` (CYA30/CYAS normalized to CYA)
- Angle: `ob` (obverse) or `rev` (reverse)

## Usage

### Quick Start (scan only)

See what will be imported:

```bash
uv run python scripts/import_dto.py --scan-only
```

### Import via API (recommended)

```bash
uv run python scripts/import_dto.py \
  --source Dataset/original \
  --api-url http://localhost:8000/api/v1 \
  --email owner@mycoai.dev \
  --password password123
```

### Import via Direct DB (no API needed)

```bash
uv run python scripts/import_dto.py --direct-db --source Dataset/original
```

### Import first N images (test run)

```bash
uv run python scripts/import_dto.py --limit 10
```

### Import with contour segmentation

```bash
uv run python scripts/import_dto.py --method contour
```

## Step-by-Step Checklist

For manual/batch processing when not using the script:

### Step 1: Ensure species exist
```bash
curl -X POST http://localhost:8000/api/v1/species \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Penicillium cyclopium"}'
```

### Step 2: Ensure media exist
```bash
curl -X POST http://localhost:8000/api/v1/media \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"CYA"}'
```

### Step 3: Upload image (auto-creates strain + segments)
```bash
curl -X POST http://localhost:8000/api/v1/images \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@DTO 148-C8 CYAob_edited.jpg" \
  -F "strain=DTO 148-C8" \
  -F "media=CYA" \
  -F "species=Penicillium cyclopium"
```

### Step 4: Batch import (if images are already accessible on server)
```bash
curl -X POST http://localhost:8000/api/v1/images/batch \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"source_dir": "/path/to/Dataset/original/subfolder", "method": "kmeans"}'
```

### Step 5: Reindex to Qdrant
```bash
curl -X POST http://localhost:8000/api/v1/index/reindex \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scope": "full_active"}'
```

### Step 6: Verify
```bash
# Check species count
curl -s http://localhost:8000/api/v1/species \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Species: {d[\"total\"]}')"

# Check image count
curl -s http://localhost:8000/api/v1/images \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Images: {d[\"total\"]}')"

# Check index status
curl -s http://localhost:8000/api/v1/index/status \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import json,sys; print(json.dumps(json.load(sys.stdin), indent=2))"
```

## Expected Output

After successful import, the backend creates per-image artifacts:

```
Dataset/uploads/{strain}/{media}/{image_id}/
├── source.jpg           # Original image
├── prepared.jpg         # 256x256 preprocessed
├── bbox_kmeans.jpg      # Bounding box overlay
├── pipeline_kmeans.jpg  # 3-panel visualization
└── segments/
    ├── segment_0.jpg    # Cropped colony
    ├── segment_1.jpg
    └── segment_2.jpg
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | No/invalid token | Re-run `login` step |
| `Source directory not found` | Wrong path | Use absolute path or check `--source` |
| `No feature extraction` | OpenCV not installed | `uv sync --all-groups` (includes opencv-python-headless) |
| `Qdrant connection refused` | Qdrant not running | `mise run qdrant-up` |
| `Images already exist` | Duplicate import | Check `GET /api/v1/images` first |

## Log Output

The script logs each step with structured format:

```
2026-01-01 12:00:00 [INFO] dto-import: Scanning dataset root: Dataset/original
2026-01-01 12:00:01 [INFO] dto-import: Scan complete: 15 species, 8 media, 496 images
2026-01-01 12:00:01 [INFO] dto-import: === Step 1: Registering 15 species ===
2026-01-01 12:00:01 [INFO] dto-import:   species: Penicillium commune
2026-01-01 12:00:02 [INFO] dto-import: === Step 2: Registering 8 media ===
2026-01-01 12:00:02 [INFO] dto-import:   media: CYA
2026-01-01 12:00:03 [INFO] dto-import: === Step 3: Uploading 496 images ===
2026-01-01 12:00:05 [INFO] dto-import:   progress: 20/496 images (4.2 img/s, 58 segments)
...
2026-01-01 12:05:00 [INFO] dto-import: === Step 4: Triggering Qdrant reindex ===
2026-01-01 12:05:30 [INFO] dto-import:   Qdrant: 1420 points indexed
2026-01-01 12:05:30 [INFO] dto-import: === Import Complete ===
```
