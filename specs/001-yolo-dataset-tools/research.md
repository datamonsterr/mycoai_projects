# Research: YOLO Dataset Export and Crop Tools

## Decision 1: Export a flat YOLO dataset plus a separate hierarchical QC tree

- **Decision**: Write YOLO image and label pairs under one export root for platform import, and also write a human-browsable hierarchical tree with species/strain/environment leaf folders for QC assets.
- **Rationale**: Flat YOLO image/label pairs are easiest to import into annotation and training tools, while the user explicitly asked for leaf folders containing resized originals and bbox visualizations.
- **Alternatives considered**:
  - Hierarchical-only output: better for browsing, but weaker as a direct YOLO import surface.
  - YOLO split folders (`train/val/test`) immediately: unnecessary for the requested manual-curation-first workflow.

## Decision 2: Keep the curated export at `3000x3000`

- **Decision**: Use `3000x3000` as the default curated export size after center-cropping to square.
- **Rationale**: The original images are much larger than the old 256x256 processing path, and the user wants to inspect and manually curate segmentation proposals. A high-resolution export preserves detail while YOLO annotations remain resolution-independent because they are normalized.
- **Alternatives considered**:
  - Keep original pixel size: best fidelity, but more variability and heavier downstream handling.
  - Export at a smaller size such as `1024` or `2048`: lighter, but worse for manual box correction.

## Decision 3: Make preprocessing size-aware in `src/preprocessing/`

- **Decision**: Add a shared preprocessing module under `src/preprocessing/` that computes square crop, resize, Hough search bounds, blur sizes, and other size-sensitive parameters from the source image dimensions.
- **Rationale**: The current repo has stale imports to a missing `process_image`, and the remaining preprocessing logic is scattered and partly hardcoded around the legacy 256x256 path. Centralizing this in `src/preprocessing/` gives the new tools one runtime surface and fixes the user’s stated blocker.
- **Alternatives considered**:
  - Keep preprocessing logic embedded inside each CLI: faster short-term, but repeats the same image logic and keeps the repo inconsistent.
  - Preserve fixed pixel constants: simpler, but directly conflicts with the user requirement and risks bad proposals on larger images.

## Decision 4: Treat every colony bbox as class `0`

- **Decision**: Write YOLO annotations as one-class detection labels where every line starts with class id `0` and `dataset.yaml` names that class `colony`.
- **Rationale**: Bounding boxes distinguish instances of the same object type, not separate classes. The existing helper in `src/prepare/init_yolo.py` enumerates boxes and effectively turns box index into class id, which is not correct for one-class detection training.
- **Alternatives considered**:
  - Use per-box label ids (`0`, `1`, `2`): invalid semantics for the requested training workflow.
  - Introduce multiple classes per colony type: unsupported by the available data and not requested.

## Decision 5: The crop tool should consume YOLO images and labels, not only exporter metadata

- **Decision**: Build the `512x512` crop tool around YOLO image/label pairs so it can operate after later manual label correction.
- **Rationale**: If the crop tool consumed only pseudo-label metadata, it would ignore corrections made in the data platform. Reading YOLO labels makes it useful both immediately after export and after curation.
- **Alternatives considered**:
  - Crop from exporter metadata only: simpler, but locks the workflow to stale pseudo labels.
  - Store crops directly during export: useful for pseudo-label review, but not sufficient for a corrected-label workflow.

## Decision 6: Visualization should be optional and pipeline-rich

- **Decision**: Gate step-by-step visual assets behind `--visualize` and include the requested sequence `original -> preprocessed -> kmeans color dimension -> chosen foreground mask -> kmeans location -> bounding box`.
- **Rationale**: The visual pipeline is valuable for debugging and feedback but will add storage and processing overhead across the full dataset. Making it optional keeps the default run lighter while preserving the requested QC path.
- **Alternatives considered**:
  - Always generate all visualization assets: simpler behavior, but higher cost and unnecessary for non-debug runs.
  - Only write a bbox image: lighter, but does not satisfy the requested feedback surface.
