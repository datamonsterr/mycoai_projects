# Feature Specification: YOLO Dataset Export and Crop Tools

**Feature Branch**: `001-yolo-dataset-tools`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "Investigate `fungal-cv-qdrant/src/utils/reformat_dataset.py`, build new Python tools under `fungal-cv-qdrant/tools` for YOLO-format dataset export, scale-aware preprocessing, hierarchical visualization output, and 512x512 segment cropping, then run tests and iterate on feedback."

## Affected Contexts *(mandatory)*

- **Primary Repo**: `fungal-cv-qdrant`
- **Additional Touched Repos**: None
- **Shared Artifacts**: `Dataset/original/`, user-supplied export directory under `Dataset/` or another local path
- **Execution Tooling**: `uv` for Python execution and validation
- **Experiment Dependency**: Reference `fungal-cv-qdrant/src/experiments/kmeans_segmentation/run.py` for the requested step-by-step visualization contract; use `fungal-cv-qdrant/src/preprocessing/` as the runtime preprocessing and bbox proposal surface for the new tools
- **Reimplementation Boundary**: N/A, all runtime work stays inside `fungal-cv-qdrant`; no backend or frontend repo consumes these tools directly

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Export a YOLO curation dataset (Priority: P1)

As a researcher, I can run one CLI against `Dataset/original/` to generate YOLO-compatible images and labels plus hierarchical browsing outputs so I can import the result into a data platform and manually correct colony boxes before Ultralytics training.

**Why this priority**: This is the core workflow the user asked for and the rest of the tooling depends on it.

**Independent Test**: Run the exporter with `--n 1 --visualize` and verify that one image produces a YOLO image/label pair, metadata, and a hierarchical folder containing the resized original and bbox visualization.

**Acceptance Scenarios**:

1. **Given** a valid source image in `Dataset/original/`, **When** the exporter runs, **Then** it writes a square resized image, a matching YOLO label file, metadata, and optional visualization assets under the chosen output root.
2. **Given** a source image where automatic bbox detection finds no colonies, **When** the exporter runs, **Then** it still writes the image and an empty YOLO label file so the sample can be manually curated later.

---

### User Story 2 - Use scale-aware preprocessing (Priority: P2)

As a researcher, I can preprocess images with parameters derived from the input image size instead of fixed pixel constants so the pipeline remains stable for larger original images.

**Why this priority**: The user explicitly called out hardcoded Hough and related parameters as a blocker for running the same logic on larger original images.

**Independent Test**: Run preprocessing on at least one non-square source image and confirm the output uses a center crop to square, then produces consistent downstream bbox proposals and visualization steps.

**Acceptance Scenarios**:

1. **Given** a non-square source image, **When** preprocessing runs, **Then** it center-crops the longer dimension so width equals height before resizing.
2. **Given** a larger-than-legacy source image, **When** preprocessing runs, **Then** its Hough and related detection parameters are derived from image size rather than fixed values tied to the old 256x256 pipeline.

---

### User Story 3 - Crop segments from YOLO boxes (Priority: P3)

As a researcher, I can run a second CLI against YOLO images and labels to crop each annotated colony and resize it to `512x512` for downstream review or model preparation.

**Why this priority**: The segment crop step is useful after pseudo-label generation and after later manual label correction.

**Independent Test**: Run the crop tool against the `--n 1` exporter output and verify that each YOLO box becomes a `512x512` crop written to the chosen output directory.

**Acceptance Scenarios**:

1. **Given** a YOLO image and matching label file, **When** the crop tool runs, **Then** it converts normalized coordinates back to pixel coordinates, crops the region, and saves a `512x512` output image for each box.
2. **Given** an empty YOLO label file, **When** the crop tool runs, **Then** it skips crop creation for that image without failing the full run.

---

### Edge Cases

- What happens when a source image is taller than it is wide, or wider than it is tall?
- How does the exporter behave when the filename cannot be fully parsed into strain/environment/angle metadata?
- How does the pipeline behave when Hough circle detection fails and preprocessing must fall back to a simpler square workflow?
- How are bbox coordinates clamped when automatic detection or YOLO labels land on image borders?
- How does `--n` behave when the requested sample count exceeds the number of available images?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a new Python CLI under `fungal-cv-qdrant/tools` that exports a YOLO-compatible dataset from `Dataset/original/`.
- **FR-002**: The exporter MUST accept `--output` to choose the export root and `--n` to limit the number of processed images for smoke testing.
- **FR-003**: The exporter MUST center-crop non-square images so width equals height before resizing.
- **FR-004**: The exporter MUST resize the curated export image to `3000x3000` by default.
- **FR-005**: The exporter MUST run preprocessing through `fungal-cv-qdrant/src/preprocessing/` and the preprocessing code MUST derive size-sensitive parameters from the actual source image dimensions instead of hardcoded values.
- **FR-006**: The exporter MUST generate YOLO bbox label files using class id `0` for every detected colony box.
- **FR-007**: The exporter MUST write a hierarchical visualization folder where each leaf folder includes at least the resized original image and the bbox visualization image, and MUST optionally include pipeline visualization assets when `--visualize` is provided.
- **FR-008**: When `--visualize` is enabled, the exporter MUST include a pipeline visualization covering `original -> preprocessed -> kmeans color dimension -> chosen foreground mask -> kmeans location -> bounding box`.
- **FR-009**: The exporter MUST write metadata that preserves provenance such as source filename, species/strain/environment/angle when available, resized image path, and bbox pixel coordinates.
- **FR-010**: The system MUST provide a second Python CLI under `fungal-cv-qdrant/tools` that reads YOLO images and labels, crops each bbox region, and writes `512x512` segment images.
- **FR-011**: The crop CLI MUST accept `--output` and `--n` and MUST gracefully handle images with zero labels.
- **FR-012**: The implementation MUST keep the change inside `fungal-cv-qdrant` and MUST NOT introduce runtime imports from backend or frontend repos.

### Key Entities *(include if feature involves data)*

- **Source Image**: An image discovered under `Dataset/original/` with parsed metadata and original dimensions.
- **Preprocess Result**: The scale-aware preprocessing output plus intermediate debug images needed for visualization.
- **Bounding Box Proposal**: A bbox in pixel coordinates produced from the preprocessing and kmeans segmentation pipeline.
- **YOLO Annotation**: A one-class normalized bbox line paired with an exported curated image.
- **Export Record**: A metadata entry linking source image, derived outputs, parsed metadata, and bbox data.
- **Segment Crop**: A `512x512` image derived from one YOLO bbox on one curated image.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the exporter with `--n 1` produces exactly one YOLO image file, one matching YOLO label file, and one metadata entry without crashing.
- **SC-002**: Running the exporter with `--n 1 --visualize` produces the hierarchical leaf assets requested by the user, including the resized original and bbox image, plus the pipeline visualization.
- **SC-003**: Running the crop CLI against the exporter output produces `512x512` crops whose count matches the number of YOLO boxes in the processed sample.
- **SC-004**: The preprocessing and bbox proposal code paths can run against at least one original-size image without relying on fixed 256x256-only Hough assumptions.

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: `uv --directory fungal-cv-qdrant run pytest`; `uv --directory fungal-cv-qdrant run python tools/export_yolo_dataset.py --n 1 --output ../Dataset/yolo_curated_smoke --visualize`; `uv --directory fungal-cv-qdrant run python tools/crop_yolo_segments.py --input ../Dataset/yolo_curated_smoke --n 1 --output ../Dataset/yolo_crops_smoke`
- **Workflow Checks**: N/A
- **Manual Validation**: Inspect one generated hierarchical leaf folder and confirm the resized original, bbox image, and pipeline visualization look correct for the sample image
- **PR Evidence**: Example command lines, sample output paths, test results, and a short note on the `3000x3000` export decision and scale-aware preprocessing changes

## Assumptions

- `Dataset/original/` remains the canonical source location unless the new CLI later adds an input override.
- A one-class YOLO dataset with class name `colony` is sufficient for manual curation and later Ultralytics detection training.
- `3000x3000` is acceptable for curated export even if later training resizes images to a smaller input size.
- Pseudo-label generation may be imperfect, so exporter outputs must remain easy to inspect and correct rather than pretending the boxes are final ground truth.
