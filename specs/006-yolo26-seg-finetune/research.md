# Research: YOLOv26 Segmentation Finetune on Vast.ai

**Feature**: 006-yolo26-seg-finetune
**Date**: 2026-05-07

## Decision 1: Model Variant Selection

**Decision**: Use YOLOv26n-seg (nano) as primary variant with optional s (small).

**Rationale**: Vast.ai instance 36259342 has an NVIDIA GeForce RTX 2060 (6GB VRAM). YOLOv26n-seg (4.8M params, 6.0B FLOPs) fits comfortably in 6GB VRAM at imgsz=640. YOLOv26s-seg (13.1M params, 21.7B FLOPs) may fit but risks OOM at larger batch sizes. Nano variant trains faster and serves as baseline; small variant is configurable for users with larger GPUs.

**Alternatives considered**:
- YOLOv26m-seg (27.9M params): too large for 6GB VRAM at reasonable batch size
- YOLOv26x-seg (69.9M params): requires 16GB+ VRAM
- YOLOv11n-seg: older architecture, lacks YOLOv26's NMS-free inference and ProgLoss improvements

## Decision 2: Training Configuration

**Decision**: Train for 100 epochs with imgsz=640, batch=8, using one-to-one head (default, no NMS needed). Use default YOLOv26 augmentations (mosaic, mixup, hsv, scale). Single class "colony" with ID 0.

**Rationale**: YOLOv26 docs recommend 100 epochs default. Batch=8 fits 6GB VRAM with nano model. One-to-one head produces 300 detections max per image without NMS post-processing — simpler deployment. Default augmentations from ultralytics package are well-tuned for general object detection and adapt to small datasets.

**Alternatives considered**:
- Fewer epochs (50): insufficient convergence for small dataset
- Larger batch (16): likely OOM on RTX 2060
- One-to-many head (end2end=False): requires NMS, adds complexity without significant gain for single-class detection
- Custom augmentation: unnecessary given YOLOv26's built-in augmentation pipeline

## Decision 3: Dataset Split Strategy

**Decision**: Use pre-split Roboflow dataset at `Dataset/manual_labeled_data_roboflow_species/` (303 train / 45 test / 87 valid). The `dataset.yaml` already specifies `train: train/images` and `val: test/images`. Update the `path:` field to absolute at runtime.

**Rationale**: Current `dataset.yaml` has identical `train` and `val` paths (both point to `images`). This needs fixing. 80/20 split is standard for small datasets. Stratified split by filename prefix (strain identifier) to ensure each strain appears in both sets. Runtime path rewriting avoids hardcoded paths that break across machines.

**Alternatives considered**:
- K-fold cross-validation: more robust but adds training complexity; existing `yolo_cross_validation` experiment covers this separately
- 90/10 split: too few validation images for meaningful mAP measurement
- Manual split file: adds maintenance burden

## Decision 4: Vast.ai Remote Workflow

**Decision**: Use SCP for data transfer (port 61888), SSH for remote commands (port 61872). Store Vast.ai connection config in `repos/fungal-cv-qdrant/src/config.py` as a dataclass with instance ID, IP, SSH port, SCP port. Support dynamic IP via config override.

**Rationale**: SCP on dedicated port 61888 avoids contention with SSH on 61872. IP may change between instance restarts — configuration centralization allows single-point updates. The existing `tools/workspace_bootstrap.sh` provides monorepo clone + setup patterns to reuse. Direct SSH command execution is simpler than setting up a CI runner on the remote machine.

**Alternatives considered**:
- rsync over SSH: adds dependency, SCP sufficient for one-time dataset copy
- tmux/screen for persistent training: SSH disconnection handling; `nohup` + output redirection simpler
- Vast.ai CLI automation: the `vastai` CLI can manage instance lifecycle but SSH is more reliable for file transfer and command execution

## Decision 5: Bbox Schema Compatibility

**Decision**: Output bboxes from YOLOv26 in `{x, y, w, h}` format matching `DatasetItemRecord.segmentation` schema used by `_bboxes_to_schema()` in `dataset.py`. Kmeans bboxes already use this format.

**Rationale**: YOLOv26 outputs bboxes in `xywh` normalized format by default. Conversion to pixel coordinates `{x, y, w, h}` matches existing kmeans bbox schema. This ensures downstream consumers (metadata JSON, visualization) use unified format. The `DatasetItemRecord.segmentation` dict maps method name → bbox list — extending with "yolo26" key requires no schema changes.

**Alternatives considered**:
- `xyxy` format: requires conversion in every consumer
- COCO JSON format: over-engineered for per-image metadata

## Decision 6: Inference Pipeline Integration

**Decision**: Add `yolo26` as a segment method alongside existing `kmeans` and `contour` in `src/prepare/dataset.py`. Inference runs on remote Vast.ai machine, outputs written to prepared leaf directories. Metadata JSON written per image.

**Rationale**: The existing `SEGMENT_METHODS = ["kmeans", "contour"]` list and `segment_item()` dispatch pattern support adding new methods cleanly. YOLOv26 inference produces bboxes that fit the existing `_save_segment_crops()` and `draw_bbox()` pipeline. Running inference on the remote machine avoids transferring 4565 images back and forth — weights come home, inference outputs written to same mounted/shared filesystem or SCP-ed back.

**Alternatives considered**:
- Separate inference script outside dataset.py: duplicates segment crop + visualization logic
- Local inference after weight download: requires copying entire prepared dataset, slower
- Run inference as ultralytics batch: fast but doesn't integrate with existing leaf directory structure

## Decision 7: Cleanup Strategy

**Decision**: Remove `Dataset/full_image/`, `Dataset/segmented_image/`, and their metadata JSONs. Use `Dataset/manual_labeled_data_roboflow_species/` as training source (manual Roboflow labels, 8 species classes). `Dataset/yolo_full_export/` and `Dataset/yolo_full_export_partial/` are kmeans-based bbox datasets — deprecated in favor of manual Roboflow labels.

**Rationale**: `full_image/` and `segmented_image/` are pre-restructure artifacts superseded by `Dataset/prepared/` (005-dataset-restructure). Their metadata JSONs are stale. `manual_labeled_data_roboflow_species/` provides manual bounding box labels (not kmeans-generated) and species-level classification (8 Penicillium species), producing a richer training signal.

**Alternatives considered**:
- Move to archive directory: adds clutter, git history preserves them
- Keep for reference: contradicts 005 spec which explicitly calls for removal
