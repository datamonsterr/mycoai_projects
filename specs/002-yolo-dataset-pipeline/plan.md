# Implementation Plan: YOLO Dataset Pipeline

**Branch**: `002-yolo-dataset-pipeline` | **Date**: 2026-04-23 | **Spec**: `/home/dat/dev/mycoai/specs/002-yolo-dataset-pipeline/spec.md`
**Input**: Feature specification from `/specs/002-yolo-dataset-pipeline/spec.md`

## Summary

Update the plan around three concrete paths: (1) keep a relabeled species dataset and train YOLO segmentation normally on it, (2) materialize dedicated 5-fold round-robin classification datasets with `train/` and `test/` only, and (3) create colony-crop datasets plus augmentation-debug tooling for backbone fine-tuning so extractor-compatible weights can be exported from `finetune_dl/` and consumed by `src/experiments/feature_extraction/feature_extractors.py` without the classifier head.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: pandas, OpenCV, NumPy, matplotlib, PyTorch, torchvision, ultralytics  
**Package / Command Tooling**: `uv` and `uvx` for Python workflows  
**Storage**: Root-level filesystem artifacts under `Dataset/`, `results/`, `weights/`, and report markdown files under `fungal-cv-qdrant/report/`  
**Testing**: pytest, black, isort, flake8, mypy  
**Target Platform**: Linux development workspace from the monorepo root, CPU-compatible but GPU-preferred for practical training  
**Project Type**: experiment pipeline, training workflow, augmentation debugging, and feature-extractor export tooling  
**Performance Goals**: Produce reproducible segmentation and classification dataset products, 5 fold datasets with explicit train/test membership, visually validated augmentation policies, crop datasets suitable for retrieval fine-tuning, and extractor-compatible backbone weights without manual restructuring  
**Constraints**: No backend or frontend changes; no direct cross-repo imports; segmentation uses train/test only and should be trained normally; classification folds use round-robin strain reuse to satisfy 5-fold requirements; retrieval fine-tuning should use colony crops rather than raw detection outputs; training must unfreeze the last backbone block before the temporary classifier head and save classifier-free weights for extractor inference  
**Scale/Scope**: One experiment repo (`fungal-cv-qdrant`), shared root datasets/results/weights, segmentation dataset product, 5 classification fold datasets, crop dataset generation, augmentation preview tooling, and backbone fine-tuning for extractor reuse

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: all implementation stays in `fungal-cv-qdrant` plus shared root `Dataset/`, `results/`, and `weights/` artifacts.
- [x] Traceability is explicit: no product-side consumer repos are changed; extractor compatibility is internal to `fungal-cv-qdrant`.
- [x] Reimplementation is explicit: no backend or frontend repo imports or runtime coupling are introduced.
- [x] Canonical toolchains are explicit: Python execution and validation use `uv`.
- [x] Validation is explicit: feature-local pytest plus dataset generation, fold generation, augmentation preview, crop generation, visualization, and training workflow commands are required; repo-wide black/isort/flake8/mypy remain recorded when unrelated debt blocks full green status.
- [x] Definition of done is explicit: dataset inspection, fold assignment verification, augmentation preview review, crop dataset verification, weight export verification, and report updates are required before handoff.
- [x] Contract sync is explicit: report content, quickstart, and artifact contracts document the segmentation dataset, fold dataset roots, crop dataset roots, augmentation debug outputs, and backbone weight outputs.
- [x] Minimality is justified: the change extends the experiment repo rather than introducing a new cross-repo integration layer.

## Project Structure

### Documentation (this feature)

```text
specs/002-yolo-dataset-pipeline/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── yolo-dataset-pipeline.md
└── tasks.md
```

### Source Code (repository root)

```text
fungal-cv-qdrant/
├── src/experiments/
│   ├── yolo_dataset/
│   ├── yolo_segmentation/
│   ├── yolo_cross_validation/
│   ├── finetune_dl/
│   └── feature_extraction/
├── src/utils/
├── tools/
├── tests/
└── report/cross_validation/

Dataset/
├── manual_labeled_data_roboflow/
├── manual_labeled_data_roboflow_species/
├── manual_labeled_data_roboflow_species_cv/
├── [planned crop dataset roots]
└── strain_to_specy.csv

results/
├── cross_validation_yolo/
└── [planned augmentation debug outputs]

weights/
└── [fine-tuned backbone weights]
```

### Affected Repositories

| Repo Path | Type | Reason |
|-----------|------|--------|
| fungal-cv-qdrant | submodule | Owns dataset preparation, fold dataset materialization, augmentation debugging, crop dataset creation, backbone fine-tuning, feature extraction, visualization, and report generation for this feature |

**Structure Decision**: Keep all code changes inside `fungal-cv-qdrant`, with shared root artifacts used only as dataset/results/weights boundaries. Extend `src/experiments/finetune_dl/` to train on colony crop datasets derived from the YOLO datasets, and keep `src/experiments/feature_extraction/feature_extractors.py` as the downstream contract for classifier-free backbone loading.

## Phase 0: Research Outcomes

- Preserve separate segmentation and classification dataset products.
- Use 5 folds with round-robin strain reuse where species have fewer than 5 strains.
- Train YOLO segmentation normally on the relabeled species dataset.
- Build colony crop datasets for retrieval/extractor fine-tuning instead of using raw detector outputs directly.
- Add augmentation-debug visualization before large training runs.
- Train with a temporary classifier head, unfreeze the last backbone stage before the head, then export classifier-free weights for the extractor classes.

## Phase 1: Design

### Plan A: Segmentation train/test dataset and normal YOLO training

1. Keep `Dataset/manual_labeled_data_roboflow_species/` as the relabeled segmentation-ready dataset.
2. Generate a deterministic train/test manifest with no validation split.
3. Train YOLO segmentation normally on that dataset product.
4. Record split metadata, outputs, and metrics for the report.

### Plan B: Classification 5-fold round-robin datasets

1. Materialize fold datasets under `Dataset/manual_labeled_data_roboflow_species_cv/fold_*`.
2. Each fold contains `train/` and `test/` only.
3. Build one selected test strain per species per fold, using round-robin reuse when a species has fewer strains than the fold count.
4. Write `fold_assignment.csv` plus aggregate CSVs and figures under `results/cross_validation_yolo/`.

### Plan C: Colony crop dataset generation for retrieval fine-tuning

1. Create crop datasets from segmentation labels or generated masks/bounding regions.
2. Keep crop splits aligned with the parent segmentation or fold datasets.
3. Preserve traceability from each crop back to the parent image and species/strain identity.

### Plan D: Augmentation debug tooling and backbone fine-tuning for extractor reuse

1. Add an augmentation preview script that renders a grid of transformed variants from one source image/crop.
2. Choose colony-safe augmentations: small rotation, flip when biologically valid, brightness/contrast/color jitter, mild blur/noise/compression, crop jitter inside the colony region, and optional object-interior masking/cutout.
3. Reuse the `finetune_dl/train_models.py` pattern but switch inputs to the crop datasets.
4. Attach a classifier head only for supervised training.
5. Unfreeze the last backbone block before the classifier head.
6. Save backbone-only weights under `weights/` for use by `feature_extractors.py`.
7. Keep extractor inference classifier-free by removing or bypassing the classifier head during loading.

### Reporting Design

1. Update report content to mention the relabeled segmentation dataset, the fold-specific classification datasets, the crop dataset strategy, and round-robin behavior.
2. Document augmentation preview outputs, weight output paths, and which extractor classes consume them.
3. Separate dataset preparation, fold materialization, crop generation, training, and visualization evidence clearly.

## Phase 1 Artifacts

- `research.md`: updated with augmentation and crop-based fine-tuning decisions
- `data-model.md`: updated with crop datasets and augmentation debug artifacts
- `contracts/yolo-dataset-pipeline.md`: updated with crop, augmentation, and training contracts
- `quickstart.md`: updated with the new training-focused workflow

## Post-Design Constitution Check

- [x] Ownership remains entirely within `fungal-cv-qdrant` and shared root artifacts.
- [x] No cross-repo runtime coupling was introduced.
- [x] Canonical toolchains remain `uv`-based.
- [x] Validation and report-sync requirements remain explicit.
- [x] The fine-tuned weight export path remains documented as an internal experiment artifact, not a hidden integration surface.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
