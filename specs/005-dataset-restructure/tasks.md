---
description: "Task list for dataset restructure and derivation"
---

# Tasks: Dataset Restructure and Derivation

**Input**: Design documents from `/specs/005-dataset-restructure/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dataset-layout.md, quickstart.md

**Validation**: Use `uv --directory repos/fungal-cv-qdrant ...` for experiment repo validation, plus `uv run pytest tools/tests/test_dataset_sync.py` and `uv run python tools/dataset_sync.py plan ...` if sync contract/examples change.

**Organization**: Tasks grouped by user story so each story stays independently testable and shippable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch setup, impact audit, and task scaffolding for canonical dataset migration.

- [X] T001 [P] Create feature branch `005-dataset-restructure` in submodule `repos/fungal-cv-qdrant` with `git submodule update --init "repos/fungal-cv-qdrant" && git -C "repos/fungal-cv-qdrant" checkout -b "005-dataset-restructure"`
- [X] T002 [P] Audit old dataset-path assumptions across `repos/fungal-cv-qdrant/src/` and `repos/fungal-cv-qdrant/README.md` for `Dataset/original`, `Dataset/new_data`, `full_image`, `segmented_image`, and flat metadata consumers
- [X] T003 [P] Review sync path assumptions in `tools/dataset_sync.py` and `tools/tests/test_dataset_sync.py` against canonical dataset names and scopes

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define canonical dataset names, roots, metadata schema, and unified preparation surface before story work.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 ⚠️ Reopened (BUG-001) Update dataset root constants and canonical path helpers in `repos/fungal-cv-qdrant/src/config.py` — must handle letter-range skip logic and `DATASET_ROOT` env var for physical rename
- [X] T005 [P] Create canonical dataset naming, path, and provenance helpers in `repos/fungal-cv-qdrant/src/utils/`
- [X] T006 ⚠️ Reopened (BUG-001) Define path-authoritative item metadata schema in `repos/fungal-cv-qdrant/src/prepare/` — must match `instance_info`, `paths` object, `segmentation` map from BUG-001
- [X] T007 [P] Create shared preparation CLI interface for source selection, subset selection, and method selection in `repos/fungal-cv-qdrant/src/prepare/`
- [X] T008 Remove or retire split preparation entrypoints in `repos/fungal-cv-qdrant/src/utils/reformat_dataset.py` and `repos/fungal-cv-qdrant/src/utils/reformat_dataset_yolo.py` in favor of unified flow

**Checkpoint**: Canonical dataset contract, naming, and CLI surface ready for story implementation

---

## Phase 3: User Story 1 - Build readable canonical dataset (Priority: P1) 🎯 MVP

**Goal**: Create one readable canonical dataset layout with clear source collection names and prepared hierarchy.

**Independent Test**: Run canonical preparation on sample images from both source collections and verify `Dataset/prepared/{species}/{strain}/{environment}/{image_stem}/` plus retained metadata and absence of redundant top-level outputs.

### Validation for User Story 1

- [X] T009 [P] [US1] Add automated preparation-layout coverage for canonical hierarchy and fallback metadata parsing in `repos/fungal-cv-qdrant/tests/`
- [X] T010 [US1] Run canonical preparation smoke command for both source collections with sample subset via `uv --directory repos/fungal-cv-qdrant run python -m src.prepare.init ...`
- [X] T011 [US1] Manually inspect sample canonical tree under `Dataset/prepared/` for species/strain/environment/image nesting and source provenance separation

### Implementation for User Story 1

- [X] T012 [P] [US1] ⚠️ Reopened (BUG-001) Implement source collection rename and purpose documentation data in `repos/fungal-cv-qdrant/src/config.py` and `repos/fungal-cv-qdrant/src/prepare/` — must handle physical mv of source dirs
- [X] T013 [P] [US1] ⚠️ Reopened (BUG-001) Implement metadata parsing and deterministic fallback labels for species, strain, environment, and angle in `repos/fungal-cv-qdrant/src/prepare/` — must handle letter-range skip, ob/rev→directory, filename env+angle extraction
- [X] T014 [US1] ⚠️ Reopened (BUG-001) Implement canonical prepared artifact writer for `Dataset/prepared/{species}/{strain}/{environment}/{angle}/` in `repos/fungal-cv-qdrant/src/prepare/` — ob/rev as leaf dirs, segments/ per leaf with segment_1.jpg naming
- [X] T015 [US1] Generate retained item metadata and strain-species mapping outputs with exact canonical paths in `repos/fungal-cv-qdrant/src/prepare/` and `repos/fungal-cv-qdrant/src/utils/generate_strain_mapping.py`
- [X] T016 [US1] Stop generating redundant `Dataset/full_image/`, `Dataset/segmented_image/`, and duplicate flat metadata in unified preparation flow under `repos/fungal-cv-qdrant/src/prepare/`

**Checkpoint**: Canonical dataset hierarchy exists and is independently testable

---

## Phase 4: User Story 2 - Produce both segmentation views for review (Priority: P2)

**Goal**: Generate method-specific KMeans and YOLO segment outputs plus visualization assets for direct review.

**Independent Test**: Prepare sample images with KMeans-only, YOLO-only, and both-method runs; verify `segments_kmeans/`, `segments_contour/`, `bbox_*.jpg`, `pipeline_*.jpg`, matching image stems, and clear skipped/partial statuses when one method unavailable.

### Validation for User Story 2

- [X] T017 [P] [US2] Add automated coverage for method-specific segment artifact sets and partial/skipped status handling in `repos/fungal-cv-qdrant/tests/`
- [X] T018 [US2] Run sample segmentation smoke commands for KMeans-only, YOLO-only, and both methods via unified preparation entrypoint in `repos/fungal-cv-qdrant/src/prepare/`
- [X] T019 [US2] Manually inspect one sample item for `segments_kmeans/`, `segments_contour/`, `bbox_kmeans.jpg`, `bbox_contour.jpg`, `pipeline_kmeans.jpg`, and `pipeline_contour.jpg`

### Implementation for User Story 2

- [X] T020 [P] [US2] ⚠️ Reopened (BUG-001) Implement KMeans segmentation writer — bboxes stored in `segmentation.kmeans` array, cropped images saved to leaf `segments/` dir as `segment_1.jpg` etc.
- [X] T021 [P] [US2] ⚠️ Reopened (BUG-001) Implement contour segmentation writer — bboxes stored in `segmentation.contour` array, cropped images saved to leaf `segments/` dir as `segment_1.jpg` etc.
- [X] T022 [US2] Implement shared segment record generation with matching parent-image naming and exact artifact paths in `repos/fungal-cv-qdrant/src/prepare/`
- [X] T023 [US2] Implement clear missing-backend and short-segmentation failure handling in unified preparation flow under `repos/fungal-cv-qdrant/src/prepare/`

**Checkpoint**: Both segmentation methods produce independently reviewable artifact sets

---

## Phase 5: User Story 3 - Keep retrieval and sync workflows usable (Priority: P3)

**Goal**: Update retrieval consumers, instructions, and sync workflow to use canonical dataset paths without manual repair.

**Independent Test**: Run retrieval-related help/smoke commands against canonical metadata-driven paths and verify documented Drive/Vast.ai sync workflow or dry-run uses only renamed source collections and prepared hierarchy.

### Validation for User Story 3

- [X] T024 [P] [US3] Add automated coverage for metadata-driven segment path consumption in retrieval or feature-generation tests under `repos/fungal-cv-qdrant/tests/`
- [X] T025 [P] [US3] Add or update sync workflow tests for canonical dataset scopes in `tools/tests/test_dataset_sync.py`
- [X] T026 [US3] Run retrieval and preparation smoke checks with `uv --directory repos/fungal-cv-qdrant run python -m src.prepare.init --help`, `uv --directory repos/fungal-cv-qdrant run python -m src.experiments.feature_extraction.generate_features --help`, and `uv --directory repos/fungal-cv-qdrant run python -m src.utils.generate_strain_mapping`
- [X] T027 [US3] Run sync dry-run validation with `uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope [updated-scope]`
- [X] T028 [US3] Manually verify updated dataset usage and Drive/Vast.ai sync instructions against sample canonical paths

### Implementation for User Story 3

- [X] T029 [P] [US3] Migrate retrieval consumer path resolution in `repos/fungal-cv-qdrant/src/experiments/retrieval/run.py` to metadata-driven canonical segment paths
- [X] T030 [P] [US3] Migrate feature extraction, training, visualization, and related dataset consumers in `repos/fungal-cv-qdrant/src/experiments/`, `repos/fungal-cv-qdrant/src/analysis/`, and `repos/fungal-cv-qdrant/src/utils/` away from flat segment directories
- [X] T031 [US3] Update preparation checks and helper flows in `repos/fungal-cv-qdrant/src/prepare/init.py` and `repos/fungal-cv-qdrant/src/prepare/checks.py` for canonical dataset names, subset selection, and method selection
- [X] T032 [P] [US3] Update dataset instructions and canonical layout documentation in `repos/fungal-cv-qdrant/README.md`
- [X] T033 [P] [US3] Update Drive/Vast.ai sync examples, scopes, and user guidance in `tools/dataset_sync.py` and related root documentation files

**Checkpoint**: Retrieval and sync workflows operate against canonical dataset contract

---

## Phase 7: Bugfix — Source Parsing & Metadata Schema (BUG-001)

**Purpose**: Correct letter-range handling, ob/rev directory layout, consolidated metadata schema, physical rename, and downstream consumer updates.

**Bugfix**: 2026-05-07 — BUG-001

- [X] T038 [US1] [BUG-001] Implement letter-range folder skip + recursive species→strain→ob/rev tree walker for incoming_low_quality source in `repos/fungal-cv-qdrant/src/prepare/dataset.py`
- [X] T039 [US1] [BUG-001] Implement consolidated JSON metadata builder — single `{collection}_metadata.json` array per collection — in `repos/fungal-cv-qdrant/src/prepare/dataset.py`
- [X] T040 [US1] [BUG-001] Implement physical rename of source collections on disk (`original/` → `curated_primary/`, `new_data/` → `incoming_low_quality/`) in preparation flow
- [X] T041 [US2] [BUG-001] Redesign `DatasetItemRecord` dataclass to match `instance_info` + `paths` object + `segmentation` map schema in `repos/fungal-cv-qdrant/src/prepare/dataset.py`; remove separate `SegmentRecord` / `SegmentationResult` as standalone metadata entities
- [X] T042 [US3] [BUG-001] Update `upload_qdrant.py` payload mapping to consume consolidated metadata array fields: `instance_info.{species,strain,environment,angle}`, `paths.segments[n]`, `segmentation.{method}[n].bbox`
- [X] T043 [US3] [BUG-001] Update feature extractors (`generate_features.py`, `extract_finetuned_features.py`, `extract_triplet_features.py`, `extract_vit_features.py`) to consume `paths.segments` array instead of constructing flat segment paths
- [X] T044 [BUG-001] Re-generate EDA charts and staircase visualization against new consolidated metadata schema; re-compile report PDF

**Checkpoint**: Source parsing correct for real directory structure; metadata schema consistent with downstream consumers

**Purpose**: Final validation, docs sync, and PR-ready evidence capture.

- [X] T034 [P] Run repo validation commands in `repos/fungal-cv-qdrant` with `uv --directory repos/fungal-cv-qdrant run mypy src` and `uv --directory repos/fungal-cv-qdrant run flake8 src`
- [X] T035 [P] Run `uv run pytest tools/tests/test_dataset_sync.py` if sync contracts or examples changed
- [X] T036 [P] Update feature docs in `specs/005-dataset-restructure/quickstart.md` if implementation commands or validation evidence changed
- [X] T037 Capture PR-ready evidence for canonical layout, sample outputs, validation commands, and remaining risks in `specs/005-dataset-restructure/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1: Setup**: no dependencies
- **Phase 2: Foundational**: depends on Phase 1 and blocks all user stories
- **Phase 3: US1**: depends on Phase 2; MVP starts here
- **Phase 4: US2**: depends on Phase 2 and uses canonical hierarchy from US1 outputs
- **Phase 5: US3**: depends on Phase 2 and canonical metadata contract; safest after US1 and US2 artifact shapes settle
- **Phase 6: Polish**: depends on all desired stories complete

### User Story Dependencies

- **US1 (P1)**: starts after Foundational; no dependency on other stories
- **US2 (P2)**: depends on US1 canonical artifact writer and metadata shape
- **US3 (P3)**: depends on US1 metadata contract and should consume final US2 method labels when both methods supported

### Within Each User Story

- Validation tasks land before story considered complete
- Automated tests required where behavior or contracts change
- Manual dataset or sync inspection required for user-facing workflow changes
- Core parsing/path work before downstream consumer migration

### Parallel Opportunities

- T001-T003 can run in parallel
- T005-T007 can run in parallel after T004 scope agreed
- US1: T009, T012, T013 can run in parallel; T014 depends on T012-T013; T015-T016 follow T014
- US2: T017, T020, T021 can run in parallel; T022 depends on T020-T021; T023 follows T022
- US3: T024-T025 and T029-T030 and T032-T033 can run in parallel once metadata contract stable
- Polish: T034-T036 can run in parallel

---

## Parallel Example: User Story 3

```bash
# Launch validation prep together:
Task: "Add automated coverage for metadata-driven segment path consumption in repos/fungal-cv-qdrant/tests/"
Task: "Add or update sync workflow tests for canonical dataset scopes in tools/tests/test_dataset_sync.py"

# Launch consumer/doc migration together:
Task: "Migrate retrieval consumer path resolution in repos/fungal-cv-qdrant/src/experiments/retrieval/run.py"
Task: "Migrate feature extraction, training, visualization, and related dataset consumers in repos/fungal-cv-qdrant/src/experiments/, repos/fungal-cv-qdrant/src/analysis/, and repos/fungal-cv-qdrant/src/utils/"
Task: "Update dataset instructions and canonical layout documentation in repos/fungal-cv-qdrant/README.md"
Task: "Update Drive/Vast.ai sync examples, scopes, and user guidance in tools/dataset_sync.py and related root documentation files"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1
4. Validate canonical dataset hierarchy on sample subset
5. Stop for review before dual-method segmentation and downstream migrations

### Incremental Delivery

1. Setup + Foundational define names, paths, and CLI surface
2. Deliver US1 canonical hierarchy and retained metadata
3. Deliver US2 segmentation artifact sets and review visuals
4. Deliver US3 consumer migration, docs, and sync workflow
5. Finish with full validation and PR evidence

### Parallel Team Strategy

1. One developer owns config/CLI foundation
2. One developer owns canonical hierarchy + metadata writer
3. One developer owns downstream retrieval/sync migration after metadata contract stabilizes

---

## Notes

- [P] tasks target different files or separable workstreams
- All tasks include concrete file paths or command targets
- User stories remain independently testable with explicit manual checks
- No backend/frontend repo changes in this feature
