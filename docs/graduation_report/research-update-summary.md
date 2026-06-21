# Concise Research Update

## Verified updates

- Fixed dataset preparation collisions in `research/src/prepare/dataset.py`.
- Rebuilt prepared dataset from both curated and incoming sources.
- Regenerated fold manifests from real prepared segment metadata.
- Added COCO-to-YOLO segmentation conversion and fine-tuned YOLO26n-seg on Roboflow dataset (303 train, 87 val, 50 test images).
- Upgraded from YOLOv8n-seg to YOLO26n-seg: DFL-free regression, end-to-end inference without NMS, MuSGD optimizer, Progressive Loss + STAL.
- Added yolo segmentation method to `segment_item()` in dataset.py; removed contour method. Each leaf folder now contains: source, prepared, bbox_kmeans, pipeline_kmeans, bbox_yolo (no yolo pipeline).
- Registered `yolo-segmentation` experiment in `run.py` EXPERIMENT_REGISTRY.
- Created pipeline script `research/src/pipeline_segmentation.py` for end-to-end kmeans + yolo comparison.
- Generated 4x2 grid visualization comparing KMeans vs YOLO26-seg on CREA media samples.
- Patched retrieval evaluation to use fresh file-query search with held-out strain exclusion.
- Ran fresh-query retrieval smoke benchmarks.

## Verified artifacts

- Prepared segments metadata: `Dataset/prepared_segments_metadata.json`.
- Fold manifests: `Dataset/folds/*.json`.
- YOLO26-seg weights: `weights/segmentation/yolo26_seg_best.pt`.
- YOLO26 training in progress: epoch 5 mAP50 ~0.89 (box), ~0.89 (mask).
- Segmentation pipeline output: `Dataset/segmented_output_complete/` (50 samples, 50 kmeans, 50 yolo).
- KMeans vs YOLO grid: `results/segmentation_grid.png` (4 CREA samples, left=kmeans, right=yolo).
- Retrieval smoke results: `results/retrieval_fresh_smoke/` and `results/retrieval_fresh_compare/`.

## Verified metrics

- YOLO26n-seg training progress (on CPU, 30 epochs, batch 8, 303 train / 87 val):
  - Epoch 1: box mAP50 = 0.551, mask mAP50 = 0.549
  - Epoch 2: box mAP50 = 0.761, mask mAP50 = 0.758
  - Epoch 4: box mAP50 = 0.890, mask mAP50 = 0.888
  - Training continues in background to epoch 30.
- KMeans segmentation: 50/50 images successfully segmented (3 bboxes each).
- YOLO26 inference (conf=0.01, top-3): 50/50 images detected.
- Fresh-query retrieval smoke:
  - `resnet50_E1_weighted` = 6/7 = 0.8571
  - `colorhistogram_E1_{weighted,uni,relative}` = 7/7 = 1.0000 on current 7-strain smoke set

## Codebase changes

- `research/src/prepare/dataset.py` — removed contour, added yolo seg method
- `research/src/prepare.py` — yolo-segmentation experiment checks
- `research/src/run.py` — yolo-segmentation registry entry
- `research/src/experiments/yolo_segmentation/__init__.py` — new
- `research/src/experiments/yolo_segmentation/run.py` — added run_accuracy
- `research/src/pipeline_segmentation.py` — new end-to-end pipeline script
- `research/src/utils/coco_to_yolo_seg.py`
- `research/src/utils/upload_qdrant.py`
- `research/src/experiments/retrieval/run.py`
- `research/src/lib/cross_validation.py`
- `docs/graduation_report/content/02-retrieval-model.md` — updated YOLO section
- `docs/graduation_report/research-update-summary.md`
- `frontend/src/pages/Retrieve.tsx`

## Remaining gaps

- YOLO26 training ongoing (background), final metrics pending.
- Full multi-fold retrieval benchmark summary still needs final consolidation.
- Threshold/open-set experiments are not completed yet.
- Backend retrieval path is not yet reimplemented to match the new research winner.
- Frontend still needs stronger evidence/unknown-result presentation than the current default-setting update.
