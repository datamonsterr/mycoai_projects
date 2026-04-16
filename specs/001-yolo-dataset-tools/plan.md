# Implementation Plan: YOLO Dataset Export and Crop Tools

**Branch**: `001-yolo-dataset-tools` | **Date**: 2026-04-16 | **Spec**: `/home/dat/dev/mycoai/specs/001-yolo-dataset-tools/spec.md`
**Input**: Feature specification from `/home/dat/dev/mycoai/specs/001-yolo-dataset-tools/spec.md`

## Summary

Add two Python CLIs under `fungal-cv-qdrant/tools`: one to export `Dataset/original/` into a YOLO-compatible curation dataset with optional hierarchical visualization assets, and one to crop `512x512` segments from YOLO labels. Support both by centralizing square-crop and size-aware preprocessing logic in `src/preprocessing/` and exposing richer kmeans debug outputs for the requested visualization pipeline.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: OpenCV, NumPy, pandas, scikit-learn, pathlib  
**Package / Command Tooling**: `uv --directory fungal-cv-qdrant ...`  
**Storage**: Local filesystem under `Dataset/original/` and a user-supplied export path  
**Testing**: `pytest` plus CLI smoke runs against `--n 1` and manual artifact inspection  
**Target Platform**: Linux local workstation / monorepo environment  
**Project Type**: Python CLI/data-preparation utilities  
**Performance Goals**: Smoke runs with `--n 1` or `--n 2` should complete quickly enough for feedback loops; full dataset export should be reproducible and resumable by rerunning the CLI  
**Constraints**: Preserve enough detail for manual curation, use a square center crop before resizing to `3000x3000`, derive preprocessing parameters from image size rather than legacy fixed values, keep changes local to `fungal-cv-qdrant`, and avoid new cross-repo coupling  
**Scale/Scope**: Hundreds of source images, each high-resolution and potentially non-square; two new CLIs, one new shared preprocessing module, targeted tests, and light documentation updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: all code changes stay in `fungal-cv-qdrant`; outputs live in shared dataset paths only as generated artifacts.
- [x] Traceability is explicit: the requested debug pipeline references `src/experiments/kmeans_segmentation/run.py` for visualization semantics, while runtime bbox proposals come from updated code in `src/preprocessing/` and are consumed by the new CLI outputs.
- [x] Reimplementation is explicit: no backend or frontend code is touched; no cross-repo runtime imports are introduced.
- [x] Canonical toolchains are explicit: Python execution and validation use `uv`.
- [x] Validation is explicit: run `uv --directory fungal-cv-qdrant run pytest`, exporter smoke runs, crop smoke runs, and manual inspection of generated images.
- [x] Definition of done is explicit: automated checks plus manual validation of one generated sample are required before handoff.
- [x] Contract sync is explicit: add CLI contract docs under this spec and update repo documentation if command usage changes materially.
- [x] Minimality is justified: the design adds only the missing shared preprocessing module, extends the existing kmeans surface, and adds the two requested CLIs without creating a new repo or compatibility layer.

## Project Structure

### Documentation (this feature)

```text
specs/001-yolo-dataset-tools/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    └── cli.md
```

### Source Code (repository root)

```text
fungal-cv-qdrant/
├── src/preprocessing/
├── src/utils/
├── src/prepare/
├── tools/
└── tests/

Dataset/
```

**Structure Decision**: Edit `fungal-cv-qdrant/src/preprocessing/` to add shared scale-aware preprocessing and richer kmeans debug outputs, add the requested CLIs under `fungal-cv-qdrant/tools/`, add targeted tests under `fungal-cv-qdrant/tests/`, and update stale imports in existing preparation utilities only where needed to keep the repo internally consistent. The only artifact boundary crossed is from source images in `Dataset/original/` to generated outputs in a user-selected dataset export path.

## Post-Design Constitution Check

- [x] Ownership remains entirely inside `fungal-cv-qdrant`.
- [x] The kmeans-related traceability is documented in the spec, plan, and CLI contract.
- [x] No product-side reimplementation or forbidden import path is involved.
- [x] `uv` remains the only Python execution toolchain.
- [x] Verification includes automated checks, smoke runs, and manual artifact review.
- [x] The plan stays minimal: shared logic is centralized once, and both CLIs consume it.

## Complexity Tracking

No constitution violations are required for this feature.
