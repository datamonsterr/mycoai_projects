# CLI Contract: yolo_segmentation finetune

**Feature**: 006-yolo26-seg-finetune
**Date**: 2026-05-07

## Command: train

Trains a YOLOv26-seg model on the 8-class Penicillium species dataset.

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  train \
  --model-variant n \
  --epochs 30 \
  --batch 8 \
  --imgsz 640
```

**Inputs**:
- `--model-variant`: Model size (n, s, m, l, x). Default: n.
- `--epochs`: Training epochs. Default: 30.
- `--batch`: Batch size. Default: 8.
- `--imgsz`: Input image size. Default: 640.
- `--device`: Torch device. Default: 0.
- `--data-root`: Path to YOLO dataset. Default: resolves from config.

**Outputs**:
- `weights/yolo26/{variant}-seg_species_best.pt` — best checkpoint (highest val mAP)
- `weights/yolo26/{variant}-seg_species_last.pt` — final epoch checkpoint
- `results/yolo26_finetune/results.csv` — per-epoch metrics
- stdout: final mAP@50 and mAP@50-95 values

**Exit codes**: 0 on success, 1 on training failure, 2 on config error.

## Command: infer

Runs YOLOv26 inference on prepared dataset images.

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  infer \
  --weights weights/yolo26/yolo26n-seg_species_best.pt \
  --data-root Dataset/prepared \
  --limit 100
```

**Inputs**:
- `--weights`: Path to trained .pt file.
- `--data-root`: Root of prepared dataset. Default: resolves from config.
- `--limit`: Max images to process. Default: all.
- `--confidence`: Detection confidence threshold. Default: 0.25.

**Outputs** (per image, in leaf directory):
- `bbox_yolo26.jpg` — bbox visualization
- `pipeline_yolo26.jpg` — source→prepared→bbox side-by-side
- `segments/segment_yolo26_{1,2,3}.jpg` — top-3 segment crops
- `metadata.json` — `{yolo26: [{x,y,w,h,confidence}], kmeans: [{x,y,w,h}]}`

**Exit codes**: 0 on success, 1 on inference failure, 2 on config error.

## Command: remote-bootstrap

Sets up the monorepo on a remote Vast.ai machine.

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  remote-bootstrap \
  --host 1.208.108.242 \
  --ssh-port 61872 \
  --instance-id 36259342
```

**Inputs**:
- `--host`: Vast.ai instance IP.
- `--ssh-port`: SSH port (after port mapping).
- `--instance-id`: Vast.ai instance ID.

**Actions**:
1. SSH into remote machine, clone monorepo
2. Checkout feature branch
3. Run `mise install && mise trust`
4. Run `uv sync`

**Exit codes**: 0 on success, 1 on SSH/connection failure, 2 on setup failure.

## Command: remote-train

SCP dataset to remote, run training, SCP weights back.

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  remote-train \
  --host 1.208.108.242 \
  --ssh-port 61872 \
  --scp-port 61888
```

**Inputs**: Same as `remote-bootstrap` + training params from `train`.

**Actions**:
1. SCP `Dataset/manual_labeled_data_roboflow_species/` to remote
2. SSH: run `train` command
3. SCP weights + results back to local `weights/yolo26/` and `results/yolo26_finetune/`

**Exit codes**: 0 on success, 1 on transfer/execution failure.
