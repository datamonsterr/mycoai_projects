# Tasks: YOLOv26 Segmentation Finetune on Vast.ai

**Input**: Design documents from `/specs/006-yolo26-seg-finetune/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Branch creation and project initialization

- [x] T001 [P] Create feature branch in submodule: `git -C repos/fungal-cv-qdrant checkout -b 006-yolo26-seg-finetune`
- [x] T002 Add `ultralytics` dependency via `uv --directory repos/fungal-cv-qdrant add ultralytics`
- [x] T003 [P] Add YOLOv26 path config constants to `repos/fungal-cv-qdrant/src/config.py`: `YOLO_DATASET_DIR`, `YOLO_WEIGHTS_DIR`, `YOLO_RESULTS_DIR`, `YOLO_CLASS_NAMES`
- [x] T004 [P] Add `VastAiConfig` dataclass to `repos/fungal-cv-qdrant/src/config.py` with fields: instance_id, host, ssh_port, scp_port, user, remote_workspace

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Dataset cleanup and validation that MUST complete before training or inference

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Remove stale dataset directories: `Dataset/full_image/`, `Dataset/segmented_image/` and their metadata JSON files via `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py` cleanup function
- [x] T006 Validate `Dataset/manual_labeled_data_roboflow_species/` dataset integrity in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py`: check train/test/valid split structure, classes.txt has 8 species, dataset.yaml has valid paths
- [x] T007 Implement `prepare_roboflow_dataset_yaml()` in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py` — update dataset.yaml path to absolute, count train/val images from existing Roboflow split
- [x] T008 Dataset already pre-split by Roboflow (train/test/valid). Use existing split structure directly — no manual train.txt/val.txt needed.
- [x] T009 Verify import smoke test: `uv --directory repos/fungal-cv-qdrant run python -c "from src.experiments.yolo_segmentation.prepare import *"`

**Checkpoint**: Dataset clean, validated, split ready — training and inference can proceed

---

## Phase 3: User Story 1 - Clean redundant datasets and select YOLO training source (Priority: P1) 🎯 MVP

**Goal**: Stale directories gone, YOLO dataset validated, ready for training

**Independent Test**: Run cleanup, verify `Dataset/full_image/` and `Dataset/segmented_image/` absent, verify manual_labeled_data_roboflow_species has 435 paired images+labels (303 train / 45 test / 87 valid) with valid dataset.yaml

### Validation for User Story 1

- [x] T010 [US1] Manual verification: `ls Dataset/full_image/ Dataset/segmented_image/ Dataset/full_image_metadata.json Dataset/segmented_image_metadata.json 2>&1` — all should report "No such file or directory"
- [x] T011 [US1] Verify dataset integrity via CLI: `uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli validate-dataset`
- [x] T012 [US1] Unit test for cleanup function in `repos/fungal-cv-qdrant/tests/test_yolo_segmentation.py` — test cleanup removes expected paths, test dataset validation reports correct counts
- [x] T013 [US1] Wire cleanup function into CLI `validate-dataset` command in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py`
- [x] T014 [US1] Add `--cleanup` flag to `validate-dataset` CLI command that triggers stale directory removal and prints summary

**Checkpoint**: User Story 1 complete — dataset clean, validated, Roboflow species training source confirmed

---

## Phase 4: User Story 2 - Finetune YOLOv26-seg on fungal species dataset via Vast.ai (Priority: P1)

**Goal**: Remote GPU training produces 8-class species detection model, weights retrieved locally

**Independent Test**: SCP dataset to remote, run training, verify best.pt and last.pt appear in local `weights/yolo26/`

### Validation for User Story 2

- [x] T015 [US2] Unit test for `FinetuneConfig` validation in `repos/fungal-cv-qdrant/tests/test_yolo_segmentation.py` — test valid configs, test OOM guard for model variant + VRAM mismatch
- [x] T016 [US2] Unit test for dataset split function in `repos/fungal-cv-qdrant/tests/test_yolo_segmentation.py` — verify 80/20 split preserves strain diversity, no image leakage
- [ ] T017 [US2] Manual validation: SSH into remote, verify training process running via `ps aux | grep yolo`, verify GPU utilization via `nvidia-smi`
- [ ] T018 [US2] Manual validation: after training completes, verify `weights/yolo26/yolo26n-seg_species_best.pt` exists locally and is valid via `uv --directory repos/fungal-cv-qdrant run python -c "from ultralytics import YOLO; m = YOLO('weights/yolo26/yolo26n-seg_species_best.pt'); print('OK')"`
- [x] T019 [P] [US2] Implement `FinetuneConfig` dataclass in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py` with model_variant, epochs, imgsz, batch, device, train_split, pretrained
- [x] T020 [P] [US2] Implement `TrainingResult` dataclass in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py` with best_map50, weights_path, last_weights_path, results_csv
- [x] T021 [US2] Implement `train_yolo26()` function in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py`: load pretrained yolo26{model_variant}-seg.pt, configure 8-class species detection, use pre-split Roboflow dataset (train/images, test/images), run model.train() with early stopping (patience=20, epochs=30), save best.pt and last.pt to `weights/yolo26/`
- [x] T022 [US2] Implement `train` CLI subcommand in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py` per contract: accept --model-variant, --epochs, --batch, --imgsz, --device, --data-root
- [x] T023 [US2] Implement GPU memory guard in `train_yolo26()`: estimate VRAM requirement from model variant, warn if exceeds RTX 2060 (6GB) threshold, abort for m/l/x variants on 6GB cards
- [x] T024 [US2] Add `nohup` wrapper for remote training in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py`: function dispatches training via SSH with `nohup ... &` and captures PID for later monitoring

**Checkpoint**: User Story 2 complete — training runs locally or remotely, weights produced

---

## Phase 5: User Story 3 - Run inference with YOLOv26 bboxes, kmeans bboxes, and visualization (Priority: P2)

**Goal**: Per-image inference outputs: segments, bbox JSON metadata, visualization images for both yolo26 and kmeans

**Independent Test**: Run infer command with --limit 5, verify each leaf directory has `bbox_yolo26.jpg`, `metadata.json`, `segments/segment_yolo26_*.jpg`

### Validation for User Story 3

- [x] T025 [US3] Unit test for YOLOv26 bbox conversion in `repos/fungal-cv-qdrant/tests/test_yolo_segmentation.py` — verify normalized xywh → pixel `{x,y,w,h}` conversion, test empty detection fallback
- [ ] T026 [US3] Unit test for metadata JSON format in `repos/fungal-cv-qdrant/tests/test_yolo_segmentation.py` — verify output matches `DatasetItemRecord.segmentation` schema
- [ ] T027 [US3] Manual validation: run inference on 5 sample images, visually inspect `bbox_yolo26.jpg` and `pipeline_yolo26.jpg` for correct bounding box overlay
- [ ] T028 [US3] Manual validation: verify `metadata.json` contains both `yolo26` and `kmeans` keys with valid bbox arrays
- [x] T029 [P] [US3] Implement `yolo26_infer_image()` in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py`: load model, run predict on single prepared image, extract top-3 bboxes by confidence, convert to `{x,y,w,h}` pixel coords
- [x] T030 [P] [US3] Implement `save_inference_artifacts()` in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py`: write `bbox_yolo26.jpg` (draw_bbox), `pipeline_yolo26.jpg` (side-by-side), `segments/segment_yolo26_{1,2,3}.jpg` (crops), `metadata.json` (`{yolo26: [...], kmeans: [...]}`)
- [x] T031 [US3] Implement `infer` CLI subcommand in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py` per contract: accept --weights, --data-root, --limit, --confidence
- [x] T032 [US3] Integrate kmeans bbox generation alongside YOLOv26 in inference loop: for each image, call existing `segment_kmeans_image()` from `src/preprocessing/kmeans.py`, include kmeans bboxes in metadata.json
- [x] T033 [US3] Handle edge cases in inference: grayscale→RGB conversion, missing source.jpg fallback (skip pipeline image), empty yolo26 detections (write empty bbox array, still produce kmeans visualization)

**Checkpoint**: User Story 3 complete — inference produces outputs for every prepared image

---

## Phase 6: User Story 4 - Remote workspace bootstrap and artifact retrieval (Priority: P3)

**Goal**: Single-command remote bootstrap, dataset transfer, training launch, weight retrieval

**Independent Test**: Run remote-bootstrap + remote-train, verify weights appear in local `weights/yolo26/`

### Validation for User Story 4

- [ ] T034 [US4] Manual validation: run `remote-bootstrap` command, verify SSH connection succeeds, monorepo cloned, branch checked out, `uv sync` completes on remote
- [ ] T035 [US4] Manual validation: run `remote-train` command, verify SCP transfers dataset, training launches remotely, weights retrieved to local `weights/yolo26/`
- [ ] T036 [US4] Manual validation: verify training continues after SSH disconnect by reconnecting and checking process still running
- [x] T037 [P] [US4] Implement `VastAiConfig.resolve()` in `repos/fungal-cv-qdrant/src/config.py`: load config from env vars or config file, support dynamic IP override
- [x] T038 [P] [US4] Implement `ssh_run()` helper in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py`: execute command over SSH with configurable host/port/user, return stdout/stderr/exit code
- [x] T039 [P] [US4] Implement `scp_transfer()` helper in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/prepare.py`: push or pull files/directories with configurable host/port
- [x] T040 [US4] Implement `remote-bootstrap` CLI subcommand in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py` per contract: SSH clone, checkout branch, `mise install && mise trust`, `uv sync`
- [x] T041 [US4] Implement `remote-train` CLI subcommand in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py` per contract: SCP dataset to remote, SSH launch `nohup` training, poll for completion or timeout, SCP weights + results back
- [x] T042 [US4] Implement `remote-infer` CLI subcommand in `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/cli.py`: SCP inference outputs back from remote, or run inference locally after weight download (user choice via --remote flag)

**Checkpoint**: User Story 4 complete — full remote workflow automated end-to-end

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final quality, documentation, and delivery readiness

- [x] T043 [P] Run lint + typecheck: `uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/yolo_segmentation/` and `uv --directory repos/fungal-cv-qdrant run mypy src/experiments/yolo_segmentation/`
- [x] T044 [P] Run all unit tests: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_yolo_segmentation.py -v`
- [x] T045 [P] Update `repos/fungal-cv-qdrant/src/config.py` docstrings for new YOLOv26 and Vast.ai config constants
- [x] T046 Update `AGENTS.md` with YOLOv26 finetune note under Active Technologies section
- [ ] T047 Validate quickstart.md workflow end-to-end: execute each command block, verify outputs match expectations
- [ ] T048 [P] PR evidence: capture training loss curve screenshot (from results.csv), sample `bbox_yolo26.jpg` visualization, sample `metadata.json`
- [ ] T049 Git commit and verify all changes on `006-yolo26-seg-finetune` branch in `repos/fungal-cv-qdrant` submodule

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup (T003, T004 config) — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational (cleanup + validation functions exist)
- **US2 (Phase 4)**: Depends on Foundational + US1 (validated dataset needed). Can run `train_yolo26()` locally to test, remote execution needs US4.
- **US3 (Phase 5)**: Depends on US2 (trained weights needed for inference). Can be tested with pretrained model before finetuning completes.
- **US4 (Phase 6)**: Depends on US2 (training command exists). Wraps US2 with remote execution.
- **Polish (Phase 7)**: Depends on all desired user stories complete.

### User Story Dependencies

- **US1 (P1)**: Independent after Foundational. No story dependencies.
- **US2 (P1)**: Depends on US1 (clean validated dataset). Can run training locally before US4.
- **US3 (P2)**: Depends on US2 (trained weights). Inference logic can be developed against pretrained model early.
- **US4 (P3)**: Depends on US2 (training command). Bootstrap logic can be tested independently with SSH before training exists.

### Within Each User Story

- Config/models before implementation
- Core function before CLI wiring
- Tests after implementation functions exist
- Manual validation after CLI wired

### Parallel Opportunities

- T001, T003, T004 can run in parallel (Setup)
- T019, T020 can run in parallel (US2 models)
- T029, T030 can run in parallel (US3 core functions)
- T037, T038, T039 can run in parallel (US4 helpers)
- T043, T044, T045, T048 can run in parallel (Polish)
- US3 inference logic (T029-T030) can be developed against pretrained YOLOv26 while US2 training runs remotely

---

## Parallel Example: User Story 2

```bash
# Launch models in parallel:
Task: "Implement FinetuneConfig dataclass in repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py"
Task: "Implement TrainingResult dataclass in repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py"

# Then implement training logic (depends on both models):
Task: "Implement train_yolo26() function..."
Task: "Implement train CLI subcommand..."

# Launch tests in parallel:
Task: "Unit test for FinetuneConfig validation..."
Task: "Unit test for dataset split function..."
```

## Parallel Example: User Story 4

```bash
# Launch SSH/SCP helpers in parallel:
Task: "Implement ssh_run() helper..."
Task: "Implement scp_transfer() helper..."
Task: "Implement VastAiConfig.resolve()..."

# Then wire CLI commands (depends on helpers):
Task: "Implement remote-bootstrap CLI subcommand..."
Task: "Implement remote-train CLI subcommand..."
```

---

## Implementation Strategy

### MVP First (US1 + US2 local only)

1. Complete Phase 1: Setup → config + dependencies
2. Complete Phase 2: Foundational → cleanup + validate + split
3. Complete Phase 3: US1 → CLI cleanup/validate commands
4. Complete Phase 4: US2 → local training with `train` command
5. **STOP and VALIDATE**: Run local training on CPU (1 epoch smoke test), verify weights saved, verify mAP output
6. Then add US4 remote execution, US3 inference

### Incremental Delivery

1. Setup + Foundational → config ready, dataset clean
2. US1 → dataset validated, training source confirmed (MVP!)
3. US2 → model trains locally, weights produced
4. US4 → remote execution automated → real GPU training
5. US3 → inference on full prepared dataset with outputs
6. Polish → lint, tests, docs, PR

### Suggested MVP Scope

US1 + US2 (local training smoke test only) — delivers clean dataset and working training pipeline. Remote execution (US4) and full inference (US3) are fast-follow.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US2 training can be smoke-tested on CPU locally (1 epoch, batch=1) before Vast.ai GPU run
- US3 inference logic can be developed and tested against pretrained `yolo26n-seg.pt` before finetuning completes
- US4 bootstrap must handle first-time SSH host key prompt (manual step per SC-004 allowing ≤3 manual interventions)
- `Dataset/prepared/` has 4565 images — inference `--limit` flag critical for testing
- Commit after each phase or logical group
- All tasks use `uv --directory repos/fungal-cv-qdrant` for Python execution per Constitution VI
