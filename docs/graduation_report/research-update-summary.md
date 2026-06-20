# Concise Research Update

## Verified updates

- Fixed dataset preparation collisions in `research/src/prepare/dataset.py`.
- Rebuilt prepared dataset from both curated and incoming sources.
- Regenerated fold manifests from real prepared segment metadata.
- Added COCO-to-YOLO segmentation conversion and trained a YOLOv8n-seg smoke model.
- Patched retrieval evaluation to use fresh file-query search with held-out strain exclusion.
- Ran fresh-query retrieval smoke benchmarks.

## Verified artifacts

- Prepared segments metadata: `Dataset/prepared_segments_metadata.json` with 3592 rows.
- Fold manifests: `Dataset/folds/*.json`.
- YOLO segmentation metrics: `results/cross_validation_yolo/segmentation/segmentation_metrics.json`.
- YOLO weights: `weights/segmentation/yolo_segmentation_best.pt`.
- Retrieval smoke results: `results/retrieval_fresh_smoke/` and `results/retrieval_fresh_compare/`.

## Verified metrics

- YOLO smoke run:
  - box mAP50 = 0.9522
  - box mAP50-95 = 0.7495
  - mask mAP50 = 0.9437
  - mask mAP50-95 = 0.6329
- Fresh-query retrieval smoke:
  - `resnet50_E1_weighted` = 6/7 = 0.8571
  - `colorhistogram_E1_{weighted,uni,relative}` = 7/7 = 1.0000 on current 7-strain smoke set

## Codebase changes

- `research/src/prepare/dataset.py`
- `research/src/utils/reformat_dataset.py`
- `research/src/utils/reformat_dataset_yolo.py`
- `research/src/utils/build_fold_manifests.py`
- `research/src/utils/coco_to_yolo_seg.py`
- `research/src/experiments/yolo_segmentation/run.py`
- `research/src/utils/upload_qdrant.py`
- `research/src/experiments/retrieval/run.py`
- `research/src/lib/cross_validation.py`
- `docs/graduation_report/content/02-retrieval-model.md`
- `frontend/src/pages/Retrieve.tsx`

## Remaining gaps

- Full multi-fold retrieval benchmark summary still needs final consolidation.
- Threshold/open-set experiments are not completed yet.
- Backend retrieval path is not yet reimplemented to match the new research winner.
- Frontend still needs stronger evidence/unknown-result presentation than the current default-setting update.
