# Tasks: YOLO Dataset Pipeline

**Input**: Design documents from `/specs/002-yolo-dataset-pipeline/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Validation**: Every task list MUST include context-appropriate verification tasks for each touched repo. Command-oriented tasks and documentation MUST use canonical toolchains: `uv`/`uvx` for Python contexts and `gh` for workflow and PR operations. Automated tests are required because dataset behavior, augmentation policy, crop generation, training workflows, and extractor/report contracts are changing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize the affected experiment repo branch and scaffold the new workflow surfaces.

- [ ] T001 [P] Create the feature branch in `fungal-cv-qdrant` with `git submodule update --init "fungal-cv-qdrant" && git -C "fungal-cv-qdrant" checkout -b "002-yolo-dataset-pipeline"`
- [X] T002 Create the augmentation, crop-generation, segmentation, and fine-tuning workflow module skeletons in `fungal-cv-qdrant/src/experiments/` and `fungal-cv-qdrant/tools/`
- [X] T003 [P] Create report/debug output scaffolds referenced by this feature in `fungal-cv-qdrant/report/cross_validation/` and `results/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared parsing, split, and artifact helpers that block all user stories.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Add unit tests for DTO strain parsing, species-manifest stability, and segmentation label rewriting in `fungal-cv-qdrant/tests/test_yolo_dataset_pipeline.py`
- [X] T005 [P] Add unit tests for 5-fold round-robin strain selection and train/test leakage protection in `fungal-cv-qdrant/tests/test_yolo_cross_validation.py`
- [X] T006 [P] Add unit tests for augmentation preview and crop dataset assignment helpers in `fungal-cv-qdrant/tests/test_yolo_visualization.py` and a new `fungal-cv-qdrant/tests/test_yolo_crop_dataset.py`
- [X] T007 Implement shared strain parsing, species mapping, manifest, and label-rewriting helpers in `fungal-cv-qdrant/src/utils/yolo_dataset_pipeline.py`
- [X] T008 Implement shared fold-building, fold-summary, and fold-materialization helpers in `fungal-cv-qdrant/src/utils/yolo_cross_validation.py`
- [ ] T009 Register shared exports for the new dataset, fold, crop, and training helpers in `fungal-cv-qdrant/src/utils/__init__.py`

**Checkpoint**: Shared dataset and fold primitives are tested and reusable.

---

## Phase 3: User Story 1 - Build species-labeled training data (Priority: P1) 🎯 MVP

**Goal**: Transform the manually labeled Roboflow dataset into a species-labeled derivative and provide augmentation-debug evidence before model training.

**Independent Test**: Run the dataset preparation entrypoint and the augmentation debug entrypoint, verify species-specific relabeling, preserved geometry, and a visual preview grid for the chosen augmentation policy.

### Validation for User Story 1 (REQUIRED) ⚠️

- [ ] T010 [P] [US1] Add dataset relabeling integration tests covering preserved split layout and rewritten species labels in `fungal-cv-qdrant/tests/test_yolo_dataset_pipeline.py`
- [X] T011 [P] [US1] Add augmentation preview tests for one-image debug rendering in `fungal-cv-qdrant/tests/test_yolo_visualization.py`
- [X] T012 [US1] Run dataset and augmentation validation with `uv --directory fungal-cv-qdrant run pytest tests/test_yolo_dataset_pipeline.py tests/test_yolo_visualization.py`
- [ ] T013 [US1] Manually inspect at least one relabeled annotation per species and one augmentation preview grid under `Dataset/` and `results/`

### Implementation for User Story 1

- [X] T014 [US1] Implement the species-labeled dataset export CLI in `fungal-cv-qdrant/src/utils/yolo_dataset_pipeline.py`
- [X] T015 [US1] Add the runnable dataset preparation entrypoint in `fungal-cv-qdrant/src/experiments/yolo_dataset/run.py`
- [X] T016 [US1] Implement the augmentation debug script that renders a preview grid from one image/crop in `fungal-cv-qdrant/tools/` or `fungal-cv-qdrant/src/experiments/`
- [X] T017 [US1] Document the relabeled dataset and augmentation-debug command surfaces in `fungal-cv-qdrant/report/cross_validation/content.md`

**Checkpoint**: User Story 1 should produce a usable relabeled dataset and a validated augmentation preview independently.

---

## Phase 4: User Story 2 - Train YOLO segmentation on colony labels (Priority: P2)

**Goal**: Train YOLO segmentation normally on the relabeled dataset using a train/test manifest with no validation split.

**Independent Test**: Generate the train/test manifest, launch the segmentation training entrypoint, and verify that the workflow writes split metadata and training outputs without creating a validation partition.

### Validation for User Story 2 (REQUIRED) ⚠️

- [X] T018 [P] [US2] Add tests for deterministic segmentation train/test manifest creation in `fungal-cv-qdrant/tests/test_yolo_dataset_pipeline.py`
- [X] T019 [US2] Run segmentation validation with `uv --directory fungal-cv-qdrant run pytest tests/test_yolo_dataset_pipeline.py`
- [ ] T020 [US2] Manually verify that the segmentation workflow uses only train/test artifacts and that the output metadata records the split clearly

### Implementation for User Story 2

- [X] T021 [US2] Implement segmentation train/test manifest generation in `fungal-cv-qdrant/src/utils/yolo_dataset_pipeline.py`
- [X] T022 [US2] Add the normal YOLO segmentation training orchestration entrypoint in `fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py`
- [X] T023 [US2] Persist segmentation metrics and split metadata for reporting in `fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py`
- [X] T024 [US2] Add segmentation workflow usage notes and artifact paths to `fungal-cv-qdrant/report/cross_validation/content.md`

**Checkpoint**: User Story 2 should run independently once the relabeled dataset exists.

---

## Phase 5: User Story 3 - Evaluate species classification with strain-held-out cross validation (Priority: P3)

**Goal**: Materialize 5-fold round-robin classification datasets, build colony-crop datasets for retrieval-style training, fine-tune backbones with a temporary classifier head, and export classifier-free weights compatible with `feature_extractors.py`.

**Independent Test**: Execute fold materialization, verify per-fold train/test integrity, generate crop datasets that inherit the parent splits, run fine-tuning on those crop datasets, and confirm the exported weights load into extractor classes without classifier inference.

### Validation for User Story 3 (REQUIRED) ⚠️

- [X] T025 [P] [US3] Add tests for fold dataset assignment, round-robin species behavior, and train/test leakage detection in `fungal-cv-qdrant/tests/test_yolo_cross_validation.py`
- [X] T026 [P] [US3] Add tests for crop dataset generation and split inheritance in `fungal-cv-qdrant/tests/test_yolo_crop_dataset.py`
- [X] T027 [P] [US3] Add tests for backbone weight export compatibility with `fungal-cv-qdrant/src/experiments/feature_extraction/feature_extractors.py`
- [X] T028 [US3] Run classification/fine-tuning validation with `uv --directory fungal-cv-qdrant run pytest tests/test_yolo_cross_validation.py tests/test_yolo_crop_dataset.py`

- [ ] T029 [US3] Manually inspect one fold dataset, one crop dataset, exported weights, and cross-validation summary artifacts under `Dataset/`, `weights/`, and `results/cross_validation_yolo/`

### Implementation for User Story 3

- [X] T030 [US3] Implement the 5-fold round-robin classification dataset materializer in `fungal-cv-qdrant/src/experiments/yolo_cross_validation/run.py`
- [X] T031 [US3] Implement aggregate CSVs and fold visualizations in `fungal-cv-qdrant/src/utils/yolo_cross_validation.py` and `fungal-cv-qdrant/src/experiments/yolo_cross_validation/visualize.py`
- [X] T032 [US3] Implement colony-crop dataset generation from segmentation labels or masks in `fungal-cv-qdrant/src/experiments/finetune_dl/` or `fungal-cv-qdrant/tools/`
- [X] T033 [US3] Implement backbone fine-tuning on crop datasets with a temporary classifier head and last-block unfreezing in `fungal-cv-qdrant/src/experiments/finetune_dl/train_models.py` or a new YOLO-specific sibling module
- [X] T034 [US3] Export classifier-free backbone weights and align their loading contract in `fungal-cv-qdrant/src/experiments/feature_extraction/feature_extractors.py`
- [X] T035 [US3] Update the experiment report with fold dataset roots, crop dataset strategy, augmentation notes, and exported weight paths in `fungal-cv-qdrant/report/cross_validation/content.md`


**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation sync, and PR-ready evidence.

- [X] T036 [P] Update quickstart and any relevant `fungal-cv-qdrant/README.md` guidance for augmentation preview, crop generation, segmentation training, and extractor fine-tuning
- [X] T037 [P] Run full feature-local validation with `uv --directory fungal-cv-qdrant run pytest tests/test_yolo_dataset_pipeline.py tests/test_yolo_cross_validation.py tests/test_yolo_visualization.py tests/test_yolo_crop_dataset.py`
- [ ] T038 Run the quickstart workflow and record output paths for the relabeled dataset, segmentation outputs, fold datasets, crop datasets, augmentation previews, and exported weights in `specs/002-yolo-dataset-pipeline/quickstart.md` or supporting evidence
- [ ] T039 Document repo-wide black/isort/flake8/mypy blockers versus feature-local validation evidence in `specs/002-yolo-dataset-pipeline/plan.md` or the final PR summary
- [ ] T040 Prepare PR-ready validation notes, manual inspection evidence, and remaining-risk summary in `specs/002-yolo-dataset-pipeline/plan.md` or the final PR summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001-T003 start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion; blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational completion.
- **User Story 2 (Phase 4)**: Depends on User Story 1 outputs because segmentation consumes the relabeled dataset and its manifest.
- **User Story 3 (Phase 5)**: Depends on User Story 1 outputs for relabeled data, and can optionally reuse User Story 2 segmentation artifacts when crop generation is mask-driven rather than label-driven.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependency Graph

```text
US1 (relabeled dataset + augmentation preview)
├──> US2 (normal YOLO segmentation train/test)
└──> US3 (5-fold classification datasets -> crop datasets -> backbone fine-tuning)

Setup -> Foundational -> US1 -> {US2, US3} -> Polish
```

### Within Each User Story

- Tests precede implementation updates for the same behavior.
- Shared helpers land before story-specific runners.
- Relabeled dataset generation precedes segmentation, fold materialization, crop generation, and fine-tuning.
- Fold materialization precedes crop generation for classification.
- Crop dataset generation precedes backbone fine-tuning.
- Fine-tuning precedes extractor weight export verification.

### Parallel Opportunities

- T001 and T003 can run in parallel at setup.
- T004, T005, and T006 can run in parallel because they target different test files.
- After US1 completes, US2 and the early US3 fold-materialization work can proceed in parallel.
- T025, T026, and T027 can run in parallel inside US3 validation.
- T036 and T037 can run in parallel during polish.

---

## Parallel Example: User Story 3

```bash
# Validation tasks for the classification/fine-tuning story
Task: "T025 Add tests for fold dataset assignment and round-robin behavior"
Task: "T026 Add tests for crop dataset generation and split inheritance"
Task: "T027 Add tests for extractor-compatible weight export"

# After fold datasets exist, crop generation and visualization can be developed alongside report updates
Task: "T031 Implement aggregate CSVs and fold visualizations"
Task: "T032 Implement colony-crop dataset generation"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Setup.
2. Complete Foundational helpers and tests.
3. Complete User Story 1 to produce the relabeled dataset and augmentation preview.
4. Validate the relabeled dataset and augmentation policy independently.

### Incremental Delivery

1. Deliver US1 to establish the shared dataset and augmentation baseline.
2. Deliver US2 for normal YOLO segmentation training on the relabeled dataset.
3. Deliver US3 for fold materialization, crop generation, and backbone fine-tuning/export.
4. Finish with cross-cutting validation and PR evidence.

### Dependency-Graph Execution

1. Execute Setup and Foundational tasks sequentially, using [P] tasks in parallel when possible.
2. Treat US1 as the root dependency node.
3. Fan out into US2 and US3 after US1 artifacts are available.
4. In US3, materialize folds before crop generation, and crop generation before fine-tuning.
5. Merge back into Polish once both branches are complete.

---

## Notes

- [P] tasks indicate separate files or independent validation work.
- US2 and US3 both rely on the relabeled species dataset from US1.
- Retrieval fine-tuning should use colony-centric crops, not raw detector outputs directly.
- Keep all implementation inside `fungal-cv-qdrant` and shared root artifact paths only.
- Do not reuse legacy cross-validation outputs in `report/week_1_2/`; write new artifacts under `results/cross_validation_yolo/`.
