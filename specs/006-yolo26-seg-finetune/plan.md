# Implementation Plan: YOLOv26 Segmentation Finetune on Vast.ai

**Branch**: `006-yolo26-seg-finetune` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-yolo26-seg-finetune/spec.md`

## Summary

Finetune a COCO-pretrained YOLOv26-seg model on the 435-image fungal colony dataset (`Dataset/manual_labeled_data_roboflow_species/`, 8 Penicillium species classes, manual Roboflow labels) on a remote Vast.ai GPU instance. Clean up stale pre-restructure dataset directories. Run inference on the full `Dataset/prepared/` corpus producing YOLOv26 + kmeans bbox metadata, segment crops, and visualization overlays per image. Provide automated remote bootstrap, SCP data transfer, and weight retrieval scripts.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: `ultralytics` (YOLOv26), `opencv-python` (existing), `numpy` (existing), `pandas` (existing)
**Package / Command Tooling**: `uv`/`uvx` for Python, `scp` + `ssh` for Vast.ai remote ops
**Storage**: Local filesystem at `Dataset/manual_labeled_data_roboflow_species/`, `Dataset/prepared/`, `weights/yolo26/`, `results/`
**Testing**: pytest in `repos/fungal-cv-qdrant/tests/`, ruff lint, mypy typecheck
**Target Platform**: Linux (remote Vast.ai GPU instance + local dev workstation)
**Project Type**: ML experiment + deployment scripts
**Performance Goals**: Training <8 hours, inference <2 hours for full prepared dataset (~4565 images)
**Constraints**: Remote GPU instance with dynamic IP, single SSH hop via non-standard port
**Scale/Scope**: 435 training images, 4565 inference images, 1 model variant, 1 GPU instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **Ownership**: All code changes confined to `repos/fungal-cv-qdrant/`. Shared artifacts (`Dataset/`, `weights/`, `results/`) updated at monorepo root per existing conventions. Backend and frontend repos NOT touched.
- [x] **Traceability**: Inference consumes `Dataset/prepared/` produced by `repos/fungal-cv-qdrant/src/prepare/dataset.py:prepare_dataset()`. YOLO training dataset at `Dataset/manual_labeled_data_roboflow_species/` produced by `repos/fungal-cv-qdrant/src/utils/yolo_dataset_pipeline.py:prepare_species_labeled_dataset()`. Producer commands and artifacts named.
- [x] **Reimplementation Boundary**: N/A — all work stays inside `repos/fungal-cv-qdrant`. No product repo imports experiment code.
- [x] **Canonical Toolchains**: Python work uses `uv`/`uvx`. No raw `pip` or `python -m pip` commands.
- [x] **Validation**: `ruff check src/`, `mypy src/prepare/`, `pytest tests/`, import smoke test for new modules.
- [x] **Definition of Done**: Local checks pass, Vast.ai training completes, weights downloaded, inference outputs verified for 5+ samples, PR with screenshots and evidence.
- [x] **Contract Sync**: No producer/consumer contract changes — existing `DatasetItemRecord.segmentation` schema is consumed as-is, not modified. Config additions documented in `repos/fungal-cv-qdrant/src/config.py`.
- [x] **Minimality**: No new shared schemas, no cross-repo coupling. New code is training + inference scripts within existing experiment structure.

## Project Structure

### Documentation (this feature)

```text
specs/006-yolo26-seg-finetune/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (repository root)

```text
repos/fungal-cv-qdrant/
├── src/
│   ├── config.py                           # EDIT: add yolo26 paths, Vast.ai config
│   ├── experiments/
│   │   └── yolo_segmentation/              # EDIT: add finetune + inference logic
│   │       ├── run.py                      # EDIT: training + inference entrypoints
│   │       ├── cli.py                      # EDIT: CLI wrapper
│   │       └── prepare.py                  # NEW: Vast.ai bootstrap + SCP helpers
│   └── utils/
│   ├── yolo_dataset_pipeline.py           # REFERENCE: producer of roboflow species dataset
│
Dataset/
├── manual_labeled_data_roboflow_species/   # Training source (435 images, 8 classes, Roboflow labels)
├── prepared/                               # Inference target (4565 images)
├── full_image/                             # REMOVE (stale)
├── full_image_metadata.json                # REMOVE (stale)
├── segmented_image/                        # REMOVE (stale)
└── segmented_image_metadata.json           # REMOVE (stale)
│
weights/
└── yolo26/                                 # NEW: model checkpoints
    ├── yolo26n-seg_species_best.pt
    └── yolo26n-seg_species_last.pt
│
results/
└── yolo26_finetune/                        # NEW: training logs, metrics
```

**Structure Decision**: All changes in `repos/fungal-cv-qdrant/`. Training and inference logic added to existing `src/experiments/yolo_segmentation/` experiment package. No new experiment package needed — this is an enhancement of the existing yolo_segmentation experiment to support YOLOv26 + Vast.ai remote execution. Shared artifacts at monorepo root follow existing conventions.

### Affected Repositories

| Repo Path | Type | Reason |
|-----------|------|--------|
| repos/fungal-cv-qdrant | submodule | Primary: training script, inference, dataset cleanup, Vast.ai bootstrap |

## Complexity Tracking

> No violations. All gates pass.
