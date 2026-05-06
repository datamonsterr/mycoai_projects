# Data Model: Dataset Restructure and Derivation

## 1. Source Dataset Collection
- **Purpose**: Top-level input collection representing one provenance/quality class of raw images.
- **Fields**:
  - `collection_name`: readable stable name
  - `quality_tier`: curated or incoming/lower-quality
  - `intended_uses`: retrieval holdout, YOLO curation, review, etc.
  - `source_root`: path to source images
- **Relationships**:
  - Contains many `Canonical Dataset Item` records.

## 2. Canonical Dataset Item

**Bugfix**: 2026-05-07 — BUG-001: redesigned from scattered `_path`-suffixed fields to `paths` object, `instance_info`, and `segmentation` map.

- **Purpose**: One prepared source image placed into canonical hierarchy with angle (ob/rev) as leaf directory.
- **Fields**:
  - `item_id`: UUID5 derived from stable source path components (species + strain + environment + angle). Needed so Qdrant, retrieval holdout, and fine-tune consumers can re-look up the same canonical item after a re-preparation run — the UUID is deterministic across runs.
  - `source_collection`: `curated_primary` or `incoming_low_quality`
  - `instance_info`: `{species, strain, environment, angle}` — flat, not nested under `data`
  - `paths`: `{source, prepared, segments: [str, ...], bbox_kmeans, bbox_contour, pipeline_kmeans, pipeline_contour}`
  - `segmentation`: `{kmeans: [{x, y, w, h}, ...], contour: [{x, y, w, h}, ...]}`
  - `source_filename`: original input filename
  - `parse_status`: `parsed` or `fallback`
- **Validation Rules**:
  - Must belong to exactly one source collection.
  - Must resolve to one canonical species/strain/environment/angle directory.
  - Must preserve source provenance even when metadata fields are unknown.
  - `item_id` MUST NOT change across re-preparation of the same source image.
  - `paths.segments` MUST list absolute or workspace-relative paths to cropped colony images.

## 3. Segmentation BBox Map

**Bugfix**: 2026-05-07 — BUG-001: replaced separate Segmentation Artifact Set + Segment Artifact entities with inline `segmentation` map in item record.

- **Purpose**: Per-method bounding box coordinates stored directly in the item's `segmentation` field.
- **Fields**: `segmentation: {kmeans: [{x: int, y: int, w: int, h: int}, ...], contour: [...]}`
- **Relationships**: Belongs to one `Canonical Dataset Item` record; no separate rows or IDs.
- **Validation Rules**: Method key must match one of `kmeans`, `contour`, or `yolo`. Empty array means no colonies detected for that method.

## 4. Consolidated Metadata JSON

**Bugfix**: 2026-05-07 — BUG-001: replaces per-image `item.json` files.

- **Purpose**: Single JSON array at `Dataset/{collection}_metadata.json` containing all item records.
- **Fields**: Array of `Canonical Dataset Item` records (each with `item_id`, `paths`, `instance_info`, `segmentation`).
- **Relationships**: One array per source collection.
- **Validation Rules**: Must be valid JSON. Every `paths.segments[n]` must resolve to an existing file. No legacy `item.json` files permitted in the output tree.

## 5. Leaf Segments Directory

- **Purpose**: Each `ob/` or `rev/` leaf directory contains a `segments/` subdirectory with cropped colony images.
- **Naming**: `segment_1.jpg`, `segment_2.jpg`, `segment_3.jpg` — 1-indexed, no method prefix.
- **Paths**: Stored in parent item's `paths.segments` array as workspace-relative strings.

## 6. Strain-Species Mapping
- **Purpose**: Stable lookup for strain-level evaluation and dataset labeling.
- **Fields**:
  - `strain`
  - `species`
  - `test_flag` when applicable
  - optional split/fold metadata
- **Relationships**:
  - Used by source parsing, retrieval evaluation, and training workflows.

## 7. Sync Profile
- **Purpose**: Defines supported upload/download scopes for Drive and Vast.ai.
- **Fields**:
  - `scope_name`
  - `local_root`
  - `remote_root`
  - `subset_examples`
  - `intended_machine`: local or Vast.ai
- **Validation Rules**:
  - Must reference canonical dataset names only.
  - Must not mention removed redundant directories.

## State Transitions

### Canonical Dataset Item
1. `discovered` → source image found
2. `parsed` → metadata parsed or unknown fallback assigned
3. `prepared` → canonical prepared image written; ob/rev leaf directory created
4. `segmented` → segmentation methods executed; bbox map written to `segmentation` field; segments saved in leaf `segments/` dir
5. `indexed_ready` → consolidated metadata JSON written

## Consumer Notes

**Bugfix**: 2026-05-07 — BUG-001: consumers now read from consolidated JSON arrays instead of per-item item.json.

- Retrieval, feature extraction, Qdrant upload, and training MUST consume item records from the consolidated `Dataset/{collection}_metadata.json` array.
- Segment paths for feature extraction come from `paths.segments[n]`; bbox coordinates from `segmentation.{method}[n]`.
- Visualization workflows MUST read `paths.bbox_kmeans`, `paths.bbox_contour`, `paths.pipeline_kmeans`, `paths.pipeline_contour` from item records.
- Consumers MUST NOT construct paths from segment IDs or assume `Dataset/segmented_image/{id}.jpg`.
