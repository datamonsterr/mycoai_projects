# Data Model: YOLOv26 Segmentation Finetune

**Feature**: 006-yolo26-seg-finetune
**Date**: 2026-05-07

## Entities

### VastAiConfig (new)

Configuration for connecting to a Vast.ai GPU instance.

| Field | Type | Description |
|-------|------|-------------|
| instance_id | str | Vast.ai instance identifier (e.g., "36259342") |
| host | str | Public IP address (e.g., "1.208.108.242") |
| ssh_port | int | SSH port after port mapping (e.g., 61872) |
| scp_port | int | SCP port for file transfer (e.g., 61888) |
| user | str | SSH user (default: "root") |
| remote_workspace | Path | Workspace root on remote machine |

### FinetuneConfig (new)

Training hyperparameters for YOLOv26 finetuning.

| Field | Type | Description |
|-------|------|-------------|
| model_variant | str | Model size: "n", "s", "m", "l", "x" |
| epochs | int | Training epochs (default: 100) |
| imgsz | int | Input image size (default: 640) |
| batch | int | Batch size (default: 8) |
| device | str | Torch device (default: "0" for GPU 0) |
| train_split | float | Fraction for training (default: 0.8) |
| pretrained | bool | Use COCO pretrained weights (default: True) |

### TrainingResult (new)

Output from a training run.

| Field | Type | Description |
|-------|------|-------------|
| model_variant | str | Which model was trained |
| best_map50 | float | Best mAP@50 on validation set |
| best_map50_95 | float | Best mAP@50-95 |
| epochs_completed | int | How many epochs actually ran |
| weights_path | Path | Path to best.pt |
| last_weights_path | Path | Path to last.pt |
| results_csv | Path | Path to training results.csv |

### YoloDetection (new)

A single bounding box detection from YOLOv26 inference.

| Field | Type | Description |
|-------|------|-------------|
| x | int | Top-left x pixel coordinate |
| y | int | Top-left y pixel coordinate |
| w | int | Bbox width in pixels |
| h | int | Bbox height in pixels |
| confidence | float | Detection confidence score (0.0-1.0) |

### InferenceArtifact (new)

Per-image inference outputs written to each prepared leaf directory.

| Field | Type | Description |
|-------|------|-------------|
| image_path | Path | Path to prepared image |
| yolo26_bboxes | list[YoloDetection] | Top-3 YOLOv26 detections |
| kmeans_bboxes | list[dict] | Existing kmeans bboxes |
| metadata_json | Path | Path to metadata JSON file |
| bbox_yolo26_img | Path | Path to bbox_yolo26.jpg |
| bbox_kmeans_img | Path | Path to bbox_kmeans.jpg |
| pipeline_yolo26_img | Path | Path to pipeline_yolo26.jpg |
| segment_paths | list[Path] | Paths to segment crop images |

## Existing Entities (Referenced, Not Modified)

### DatasetItemRecord (from `src/prepare/dataset.py`)

Extended with `yolo26` key in `segmentation` dict:

```python
item_record.segmentation["yolo26"] = [{"x": 10, "y": 20, "w": 100, "h": 80}, ...]
item_record.segmentation["kmeans"] = [{"x": 5, "y": 15, "w": 95, "h": 75}, ...]
```

Paths dict extended with:
```python
item_record.paths["bbox_yolo26"] = "relative/path/to/bbox_yolo26.jpg"
item_record.paths["pipeline_yolo26"] = "relative/path/to/pipeline_yolo26.jpg"
```

### SourceCollection (from `src/prepare/dataset.py`)

Unchanged. YOLO dataset is referenced by path, not by SourceCollection.

## Directory Layout

```text
Dataset/prepared/{species}/{strain}/{environment}/{angle}/
├── source.jpg                 # existing
├── prepared.jpg               # existing
├── bbox_kmeans.jpg            # existing
├── bbox_contour.jpg           # existing
├── bbox_yolo26.jpg            # NEW
├── pipeline_kmeans.jpg        # existing
├── pipeline_contour.jpg       # existing
├── pipeline_yolo26.jpg        # NEW
├── metadata.json              # NEW (per-image bbox data)
└── segments/
    ├── segment_1.jpg          # existing (kmeans/contour)
    ├── segment_2.jpg          # existing
    ├── segment_3.jpg          # existing
    ├── segment_yolo26_1.jpg   # NEW
    ├── segment_yolo26_2.jpg   # NEW
    └── segment_yolo26_3.jpg   # NEW

weights/yolo26/
├── yolo26n-seg_species_best.pt    # NEW
├── yolo26n-seg_species_last.pt    # NEW
└── results.csv                   # NEW (training metrics)
```
