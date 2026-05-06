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
- **Purpose**: One prepared source image placed into canonical hierarchy.
- **Fields**:
  - `item_id`: stable unique id
  - `source_collection`
  - `species`
  - `strain`
  - `environment`
  - `angle`
  - `source_filename`
  - `canonical_dir`
  - `source_image_path`
  - `prepared_image_path`
  - `parse_status`: parsed or fallback/unknown metadata case
- **Validation Rules**:
  - Must belong to exactly one source collection.
  - Must resolve to one canonical species/strain/environment folder.
  - Must preserve source provenance even when metadata fields are unknown.

## 3. Segmentation Artifact Set
- **Purpose**: All derived segmentation outputs for one canonical dataset item.
- **Fields**:
  - `item_id`
  - `method`: `kmeans` or `contour`
  - `segment_count`
  - `segments_dir`
  - `bbox_visualization_path`
  - `pipeline_visualization_path`
  - `status`: success, partial, failed, skipped
- **Relationships**:
  - Belongs to one `Canonical Dataset Item`.
  - Contains many `Segment Artifact` records.
- **Validation Rules**:
  - Method label must match folder naming.
  - Matching-name convention must link sibling methods for same parent image.

## 4. Segment Artifact
- **Purpose**: One derived crop produced by a segmentation method.
- **Fields**:
  - `segment_id`
  - `item_id`
  - `method`
  - `segment_index`
  - `image_path`
  - `bbox`
  - `width`
  - `height`
- **Relationships**:
  - Belongs to one `Segmentation Artifact Set`.
- **Validation Rules**:
  - Path must exist inside method-specific segments folder.
  - Index must be unique within item + method.

## 5. Retrieval Segment Record
- **Purpose**: Segment metadata row consumed by feature extraction, training, retrieval, and Qdrant upload.
- **Fields**:
  - `segment_id`
  - `parent_item_id`
  - `species`
  - `strain`
  - `environment`
  - `angle`
  - `method`
  - `segment_path`
  - `bbox`
- **Relationships**:
  - Derived from one `Segment Artifact`.
- **Validation Rules**:
  - Must carry path-authoritative location, not inferred flat-directory path.
  - Must preserve enough labels for holdout selection and evaluation.

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
3. `prepared` → canonical prepared image written
4. `segmented_partial` or `segmented_complete` → one or both methods produced outputs
5. `indexed_ready` → retrieval segment records/materialized metadata available

### Segmentation Artifact Set
1. `pending`
2. `running`
3. `success` / `partial` / `failed` / `skipped`

## Consumer Notes
- Retrieval, feature extraction, Qdrant upload, and training should consume `Retrieval Segment Record` rows filtered by method rather than rebuilding image paths from segment ids.
- Visualization workflows should read canonical artifact paths directly from metadata.
