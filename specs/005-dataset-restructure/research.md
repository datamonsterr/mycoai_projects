# Research: Dataset Restructure and Derivation

## Decision 1: Rename source collections by purpose, not acquisition history
- **Decision**: Rename `Dataset/original` to a purpose-revealing source collection for primary curated images and rename `Dataset/new_data` to a purpose-revealing source collection for lower-quality incoming images; keep both as source-only inputs distinct from derived artifacts.
- **Rationale**: Current names describe chronology, not usage. Spec requires clearer readability and support for retrieval holdout, YOLO curation, and lower-quality review workflows.
- **Alternatives considered**:
  - Keep `original` and `new_data`: rejected because names remain ambiguous.
  - Merge both into one raw folder immediately: rejected because provenance and quality differences matter for downstream selection and debugging.

## Decision 2: One canonical derived hierarchy with explicit per-image artifact folders
- **Decision**: Store prepared outputs under one canonical hierarchy organized by species, strain, environment, and per-image artifact set, with method-specific `segments_kmeans/` and `segments_yolo/` subfolders plus visualization assets.
- **Rationale**: Current flat `full_image` and `segmented_image` stores force every consumer to reconstruct paths from ids and duplicate metadata. Per-image artifact sets preserve comparability and remove redundant copies.
- **Alternatives considered**:
  - Keep flat segment store and add hierarchy in parallel: rejected because spec explicitly removes redundant top-level copies.
  - Keep one hierarchy but mix all methods in same folder: rejected because method comparison becomes fragile.

## Decision 3: Keep metadata, but make it path-authoritative instead of path-reconstructed
- **Decision**: Retain metadata records for prepared items and segments, but require records to carry exact canonical artifact paths and method labels rather than forcing consumers to infer file locations from image ids.
- **Rationale**: Many must-change consumers currently build `SEGMENTED_IMAGE_DIR / {image_id}.jpg`; this fails once artifacts are nested. Path-authoritative metadata minimizes downstream guesswork.
- **Alternatives considered**:
  - Remove metadata entirely: rejected because retrieval, feature extraction, training, and upload flows need structured records.
  - Keep old metadata shape and derive nested paths from id: rejected because brittle and incompatible with multiple segment methods.

## Decision 4: Unify KMeans and YOLO preparation into one entrypoint with method selection
- **Decision**: Replace `src/utils/reformat_dataset.py` and `src/utils/reformat_dataset_yolo.py` with one maintained preparation entrypoint that can run KMeans, YOLO, or both methods for selected source collections/subsets.
- **Rationale**: Spec explicitly removes dual-script drift. Unified entrypoint also centralizes naming, metadata schema, and validation.
- **Alternatives considered**:
  - Leave two scripts and add wrapper: rejected because duplicate logic remains.
  - Force both methods every run: rejected because YOLO backend may be unavailable.

## Decision 5: Retrieval/training consumers must choose canonical segment method explicitly
- **Decision**: Downstream consumers that currently read flat segments must switch to reading canonical metadata filtered by segment method, using exact artifact paths from metadata.
- **Rationale**: Spec requires both segmentation methods to coexist. Retrieval, feature extraction, visualization, and training need explicit method choice instead of implicit single flat corpus.
- **Alternatives considered**:
  - Continue assuming one global segment directory: rejected because incompatible with `segments_kmeans/` and `segments_yolo/`.
  - Duplicate features for all methods automatically in all pipelines: deferred because not all consumers need both methods immediately.

## Decision 6: Full impact audit must include downstream experiment utilities and sync docs
- **Decision**: Planning scope includes all fungal-cv-qdrant consumers that mention `Dataset/original`, `Dataset/new_data`, `full_image`, `segmented_image`, `segmented_image_metadata.json`, or old diverse-data path assumptions.
- **Rationale**: User explicitly requested exploration of all necessary changes after restructure. Impact audit found config, prepare, feature extraction, retrieval, cross-validation, threshold, finetune, visualization, README, sync examples, and tests.
- **Alternatives considered**:
  - Limit changes to config plus reformat script: rejected because downstream code would silently break.

## Decision 7: Sync workflow should reuse existing dataset sync tooling
- **Decision**: Keep `tools/dataset_sync.py` as sync mechanism and update examples, scopes, and tests to match new canonical dataset names and derived artifact layout.
- **Rationale**: Existing monorepo guidance already standardizes Drive/Vast.ai sync through this tool. Fastest path is contract refresh, not new tooling.
- **Alternatives considered**:
  - Add ad hoc rclone commands to repo docs: rejected because duplicates existing supported flow.
  - Build a new dataset-only sync command: rejected as unnecessary.

## Decision 8: Historical reports are not blocker for implementation, but active docs are in scope
- **Decision**: Active operational docs and program docs must be updated; archived reports with embedded old image links are optional cleanup unless they are used as active instructions.
- **Rationale**: Spec requires instructions and sync guidance, not mass retrofitting of historical reports.
- **Alternatives considered**:
  - Update every old report path: rejected as high churn with low operational value.
  - Ignore all docs: rejected because users need new dataset instructions.
