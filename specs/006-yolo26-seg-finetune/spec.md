# Feature Specification: YOLOv26 Segmentation Finetune on Vast.ai

**Feature Branch**: `006-yolo26-seg-finetune`  
**Created**: 2026-05-07  
**Status**: Draft  
**Input**: User description: "I want to update the code since we merged @specs/005-dataset-restructure/ for yolo related code, Verify Dataset/yolo related dataset to see what is the best to use to train yolo26 seg for detect bounding box, read https://docs.ultralytics.com/vi/models/yolo26/#key-features, clean other duplicates/outdate dataset like full_images, segment_images since we will only use prepared and yolo format dataset for training. Then weights will be stored in weights of root project, using scp to copy dataset and process in the vast ai machine. This is vast ai machine information Instance ID: 36259342, Machine Copy Port: 61888, Public IP Address: 1.208.108.242, Instance Port Range: 61824-61886, Ip Address Type: Dynamic, Open Ports: 1.208.108.242:61824 -> 1111/tcp, 1.208.108.242:61872 -> 22/tcp, 1.208.108.242:61857 -> 6006/tcp, 1.208.108.242:61832 -> 61832/tcp, 1.208.108.242:61886 -> 8080/tcp, 1.208.108.242:61882 -> 8384/tcp in current session, you need to clone project, setup, checkout to branch with implementation and run then download the result back to weights. Also inference in the vast ai machine to get the result in prepared/ dataset @repos/fungal-cv-qdrant/src/prepare/dataset.py format segments/ for 3 segment, metadata with yolo26: method segmentation bboxes value, kmeans value also and visualization of image with bounding boxes in the same folder as source.jpg"

## Table of Contents

- [Affected Contexts](#affected-contexts-mandatory)
- [User Scenarios & Testing](#user-scenarios--testing-mandatory)
- [Requirements](#requirements-mandatory)
- [Success Criteria](#success-criteria-mandatory)
- [Definition of Done](#definition-of-done-mandatory)
- [Assumptions](#assumptions)

## Affected Contexts *(mandatory)*

- **Primary Repo**: `repos/fungal-cv-qdrant`
- **Additional Touched Repos**: None
- **Shared Artifacts**: `Dataset/manual_labeled_data_roboflow_species/` (training source, 8 Penicillium species, Roboflow-format labels), `Dataset/prepared/` (inference target), `weights/yolo26/` (model outputs)
- **Execution Tooling**: `uv`/`uvx` for Python workflows, `scp` for remote data transfer, `ssh` for Vast.ai remote execution
- **Experiment Dependency**: `repos/fungal-cv-qdrant/src/prepare/dataset.py` produces `Dataset/prepared/` canonical layout consumed by inference; `Dataset/manual_labeled_data_roboflow_species/` produced by `repos/fungal-cv-qdrant/src/utils/yolo_dataset_pipeline.py:prepare_species_labeled_dataset()` — 8-class Penicillium species with manual Roboflow bounding boxes (303 train / 45 test / 87 valid)
- **Reimplementation Boundary**: N/A; all work stays inside `repos/fungal-cv-qdrant`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean redundant datasets and select YOLO training source (Priority: P1)

As a researcher, I want stale dataset directories removed and a validated YOLO-format dataset ready for training so that training starts from clean, known-good data.

**Why this priority**: Dataset hygiene and verified training data are prerequisites for any model finetuning. Without clean data, training results are unreliable.

**Independent Test**: Can be fully tested by removing redundant directories, verifying manual_labeled_data_roboflow_species has valid labels and images, and confirming dataset.yaml resolves correctly.

**Acceptance Scenarios**:

1. **Given** `Dataset/full_image/` and `Dataset/segmented_image/` exist from pre-restructure layout, **When** cleanup script runs, **Then** both directories and their associated metadata JSON files are removed from `Dataset/`.
2. **Given** `Dataset/manual_labeled_data_roboflow_species/` contains 435 labeled images with 8 Penicillium species classes in Roboflow train/test/valid split, **When** researcher inspects dataset, **Then** all images have corresponding `.txt` label files, `classes.txt` lists 8 species names, and `dataset.yaml` has valid absolute paths.
3. **Given** `Dataset/yolo_full_export/` and `Dataset/yolo_full_export_partial/` are kmeans-based bbox datasets (not manual labels), **When** researcher evaluates datasets, **Then** `manual_labeled_data_roboflow_species` is confirmed as the best source (manual labels, species-level classes) and kmeans datasets are documented as deprecated.

---

### User Story 2 - Finetune YOLOv26-seg on fungal colony dataset via Vast.ai (Priority: P1)

As a researcher, I want to finetune a pretrained YOLOv26 instance segmentation model on our fungal colony dataset using a remote GPU machine, so that I get a specialized model for detecting colony boundaries without tying up my local workstation.

**Why this priority**: Model finetuning is the core deliverable. Remote execution on Vast.ai prevents local resource contention and enables GPU-accelerated training.

**Independent Test**: Can be fully tested by SCP-ing the training dataset to the Vast.ai machine, running the training script, and verifying loss curves decrease and model checkpoints are produced.

**Acceptance Scenarios**:

1. **Given** Vast.ai instance 36259342 is running at 1.208.108.242 with SSH on port 61872, **When** researcher runs the deployment script, **Then** the monorepo is cloned to the remote machine, the feature branch is checked out, and `uv sync` installs all dependencies including `ultralytics`.
2. **Given** the training dataset is uploaded to the remote machine, **When** YOLOv26-seg training launches, **Then** the model trains for the configured number of epochs using the "colony" class, producing loss metrics and checkpoint files.
3. **Given** training completes on the remote machine, **When** download script runs, **Then** the best and last model weights are SCP-ed back to `weights/yolo26/` at the monorepo root with filename indicating model variant and training date.

---

### User Story 3 - Run inference with YOLOv26 bboxes, kmeans bboxes, and visualization (Priority: P2)

As a researcher, I want to run the finetuned model on the prepared dataset and get segmentation bounding boxes from both YOLOv26 and kmeans methods, plus visual overlays, so that I can compare detection quality and build enriched metadata.

**Why this priority**: Inference and visualization close the loop on training and provide actionable outputs for downstream retrieval and analysis. Depends on trained weights existing.

**Independent Test**: Can be fully tested by running inference on a sample of prepared images and verifying output directories contain segments, bbox JSON, and visualization images for both methods.

**Acceptance Scenarios**:

1. **Given** finetuned YOLOv26 weights are available in `weights/yolo26/`, **When** inference runs on images in `Dataset/prepared/` hierarchical layout, **Then** each leaf directory gains:
   - `segments/` folder with 3 segment crop images per method
   - `bbox_yolo26.jpg` visualization with YOLOv26-predicted bounding boxes drawn
   - `bbox_kmeans.jpg` visualization with kmeans-derived bounding boxes drawn
   - `pipeline_yolo26.jpg` showing source → prepared → bbox visualization side-by-side
2. **Given** inference completes, **When** metadata is written per image, **Then** each leaf directory contains a JSON record with `yolo26` bbox schema `[{x, y, w, h}]` and `kmeans` bbox schema `[{x, y, w, h}]` matching `DatasetItemRecord.segmentation` format from `src/prepare/dataset.py`.
3. **Given** YOLOv26 model cannot detect any colony in an image, **When** inference runs, **Then** the record is marked with empty bbox arrays and the visualization still shows the prepared image for manual review.

---

### User Story 4 - Remote workspace bootstrap and artifact retrieval (Priority: P3)

As a researcher, I want a single command sequence to clone, setup, train, and retrieve results from the Vast.ai machine so that the full workflow is reproducible without manual SSH steps.

**Why this priority**: Automation of the remote workflow saves time on repeated runs and reduces human error in SCP/SSH commands. Usable once training script exists.

**Independent Test**: Can be fully tested by running the end-to-end deployment script from a clean state on the remote machine and verifying weights appear in local `weights/yolo26/`.

**Acceptance Scenarios**:

1. **Given** SSH access to Vast.ai instance is configured, **When** deployment script executes, **Then** it clones the monorepo, checks out the feature branch, runs `mise install && mise trust` and `uv sync`, copies the training dataset via SCP, and prints training start confirmation.
2. **Given** training and inference complete on the remote machine, **When** download script executes, **Then** weights, inference outputs, and training logs are retrieved via SCP and placed in the corresponding monorepo root directories.

---

### Edge Cases

- What happens when the Vast.ai instance IP address changes (dynamic IP)? How does the workflow detect and use the current SSH host/port?
- What happens when `Dataset/manual_labeled_data_roboflow_species/dataset.yaml` uses a stale absolute path from a different machine?
- How does the system handle GPU out-of-memory on the Vast.ai instance with larger model variants?
- What happens when SSH connection to Vast.ai drops mid-training?
- How does inference behave when a prepared image has no corresponding source.jpg in the same directory?
- What happens when different model variants (n/s/m/l/x) produce overlapping weight filenames in `weights/yolo26/`?
- How does the system handle the 8-class species dataset with imbalanced class distribution?
- What happens when the prepared image is grayscale and YOLOv26 expects 3-channel RGB input?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove `Dataset/full_image/`, `Dataset/full_image_metadata.json`, `Dataset/segmented_image/`, and `Dataset/segmented_image_metadata.json` from the monorepo root.
- **FR-002**: System MUST validate that `Dataset/manual_labeled_data_roboflow_species/` contains paired images and labels in Roboflow train/test/valid split structure, a valid `dataset.yaml` with resolvable paths, and a `classes.txt` with 8 Penicillium species.
- **FR-003**: System MUST provide a training script that loads a COCO-pretrained YOLOv26-seg model, configures it for 8-class Penicillium species detection, and trains on `Dataset/manual_labeled_data_roboflow_species/` with early stopping (patience=20, max 30 epochs).
- **FR-004**: Training MUST produce model checkpoint files saved to `weights/yolo26/` on the remote machine during training, with both best.pt and last.pt preserved.
- **FR-005**: System MUST use SCP to transfer `Dataset/manual_labeled_data_roboflow_species/` from the local monorepo to the Vast.ai remote machine before training begins.
- **FR-006**: System MUST use SCP to retrieve training artifacts (weights, logs, metrics) from the remote machine to local `weights/yolo26/` and `results/` after training completes.
- **FR-007**: Inference MUST process every image under `Dataset/prepared/` using both the finetuned YOLOv26 model and the existing kmeans segmentation method.
- **FR-008**: Inference MUST output per-image metadata as JSON files containing bbox arrays in `{x, y, w, h}` schema for both `yolo26` and `kmeans` methods, matching `DatasetItemRecord.segmentation` format.
- **FR-009**: Inference MUST generate visualization images: `bbox_yolo26.jpg`, `bbox_kmeans.jpg`, `pipeline_yolo26.jpg` (source → prepared → bbox side-by-side) in the same leaf directory as the source image.
- **FR-010**: Inference MUST save top-3 segment crops per method to a `segments/` subdirectory within each leaf directory.
- **FR-011**: System MUST provide a remote bootstrap script that clones the monorepo, checks out the feature branch, installs toolchain (`mise install`), and syncs Python dependencies (`uv sync`) on the Vast.ai machine.
- **FR-012**: System MUST accept Vast.ai connection parameters (instance ID, IP, SSH port) as configuration so the workflow adapts to dynamic IP assignments.
- **FR-013**: Training dataset.yaml paths MUST be rewritten at runtime to the actual machine filesystem rather than relying on hardcoded absolute paths.

### Key Entities *(include if feature involves data)*

- **YOLO Training Dataset**: 435 images at `Dataset/manual_labeled_data_roboflow_species/` with Roboflow-format train/test/valid splits (303/45/87), 8 Penicillium species classes (IDs 0-7). Manual bounding box labels from Roboflow. Described by `dataset.yaml` with train/val paths.
- **Finetuned Weights**: PyTorch checkpoint files (`.pt`) produced by YOLOv26 training, stored at `weights/yolo26/`. Includes `best.pt` (highest validation mAP) and `last.pt` (final epoch).
- **Inference Metadata**: Per-image JSON files in each prepared leaf directory containing `{yolo26: [{x, y, w, h}], kmeans: [{x, y, w, h}]}` bbox arrays matching the `DatasetItemRecord.segmentation` schema.
- **Visualization Artifacts**: Per-image JPEG files (`bbox_yolo26.jpg`, `bbox_kmeans.jpg`, `pipeline_yolo26.jpg`) showing bounding box overlays and side-by-side pipeline views.
- **Segment Crops**: Top-3 region crops per segmentation method, saved as `segments/segment_{1,2,3}.jpg` within each leaf directory.
- **Vast.ai Instance**: Remote GPU machine identified by Instance ID 36259342, accessible via SSH at `1.208.108.242:61872` with SCP data transfer on port 61888.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Redundant dataset directories (`full_image/`, `segmented_image/`) and their metadata files are absent from `Dataset/` after cleanup.
- **SC-002**: YOLOv26 finetuning completes on the Vast.ai machine within 4 hours for the nano (n) model variant on 303 training images (30 epochs with early stopping).
- **SC-003**: Finetuned model achieves at least 60% mAP@50 on the 8-class Penicillium species detection task on the held-out test set.
- **SC-004**: The end-to-end workflow (clone → setup → train → inference → download) completes with no more than 3 manual interventions for SSH host key verification.
- **SC-005**: Every image in `Dataset/prepared/` receives inference output containing both YOLOv26 and kmeans bbox metadata plus visualization images.
- **SC-006**: Segment crop images are generated for at least 85% of prepared images (accounting for images where both methods fail to detect any region).

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: `uv --directory repos/fungal-cv-qdrant run ruff check src/`, `uv --directory repos/fungal-cv-qdrant run mypy src/prepare/`, `uv --directory repos/fungal-cv-qdrant run python -c "from src.prepare.dataset import prepare_dataset, segment_item, run_segmentation"`
- **Workflow Checks**: N/A (no GitHub workflow specific to Vast.ai training exists)
- **Manual Validation**: SSH into Vast.ai instance 36259342, verify monorepo checkout at correct branch, verify training is running via `nvidia-smi` and training logs, verify weights exist in `weights/yolo26/` locally after download, verify inference outputs exist for 5+ sample images in `Dataset/prepared/`
- **PR Evidence**: Branch diff showing cleanup (removed directories), training script added, inference script added, updated config for yolo26 paths. Screenshots of training loss curves and sample visualization images attached.

## Assumptions

- Vast.ai instance 36259342 remains running with GPU available throughout training duration.
- SSH key-based authentication to the Vast.ai instance is already configured locally.
- The `ultralytics` Python package (version supporting YOLOv26) is installable via `uv` on the remote machine.
- `Dataset/manual_labeled_data_roboflow_species/` 435-image dataset with manual Roboflow labels provides superior training signal compared to kmeans-generated bboxes. 8-class species multi-class detection provides richer downstream utility.
- The 8 Penicillium species classes represent strains identified in the strain-to-species mapping at `strain_to_specy.csv`.
- `Dataset/prepared/` images are already preprocessed (resized, background removed) by the existing `process_image()` pipeline and are ready for inference.
- The remote Vast.ai machine has sufficient disk space for monorepo clone, dataset copy, and training artifacts (estimated 10-20 GB).
- YOLOv26 model variant defaults to "small" (yolo26s-seg.pt) as reasonable balance of accuracy and training speed; other variants available via configuration.
