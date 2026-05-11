# Quickstart: YOLOv26 Finetune on Vast.ai

**Feature**: 006-yolo26-seg-finetune

## Prerequisites

1. Vast.ai instance 36259342 running with GPU (NVIDIA RTX 2060)
2. SSH key configured on remote machine
3. Local monorepo with `uv` and `mise` installed

## 5-Minute Workflow

```bash
# 1. Clean stale dataset directories
uv --directory repos/fungal-cv-qdrant run python -c "
from src.config import WORKSPACE_ROOT
import shutil
for d in ['Dataset/full_image', 'Dataset/segmented_image']:
    p = WORKSPACE_ROOT / d
    if p.exists():
        shutil.rmtree(p)
        print(f'Removed {p}')
for f in ['Dataset/full_image_metadata.json', 'Dataset/segmented_image_metadata.json']:
    p = WORKSPACE_ROOT / f
    if p.exists():
        p.unlink()
        print(f'Removed {p}')
"

# 2. Bootstrap remote monorepo on Vast.ai
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  remote-bootstrap \
  --host 1.208.108.242 \
  --ssh-port 61872

# 3. Copy dataset + train + download weights
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  remote-train \
  --host 1.208.108.242 \
  --ssh-port 61872 \
  --scp-port 61888 \
  --model-variant n \
  --epochs 30

# 4. Run inference locally with downloaded weights
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.cli \
  infer \
  --weights weights/yolo26/yolo26n-seg_species_best.pt \
  --limit 10  # test first 10, then remove --limit for full run

# 5. Verify outputs
ls Dataset/prepared/*/*/*/*/bbox_yolo26.jpg | head -5
ls Dataset/prepared/*/*/*/*/metadata.json | head -5
ls weights/yolo26/
```

## Model Variants

| Variant | Params | VRAM Needed | Best For |
|---------|--------|-------------|----------|
| `n` (nano) | 4.8M | ~3GB | Baseline, fast iteration |
| `s` (small) | 13.1M | ~5GB | Better accuracy on RTX 2060 |
| `m` (medium) | 27.9M | ~8GB | Needs RTX 3070+ |
| `l` (large) | 32.3M | ~10GB | Needs RTX 3080+ |
| `x` (xlarge) | 69.9M | ~16GB | Needs RTX 4090 |

## Expected Outputs

```text
weights/yolo26/
├── yolo26n-seg_species_best.pt    # Best validation mAP checkpoint
├── yolo26n-seg_species_last.pt    # Final epoch checkpoint
└── results.csv                   # Per-epoch training metrics

Dataset/prepared/{species}/{strain}/{env}/{angle}/
├── bbox_yolo26.jpg               # YOLOv26 bbox overlay
├── pipeline_yolo26.jpg           # Side-by-side pipeline view
├── metadata.json                 # {yolo26: [...], kmeans: [...]}
└── segments/
    └── segment_yolo26_{1,2,3}.jpg  # Top-3 YOLOv26 segment crops
```
