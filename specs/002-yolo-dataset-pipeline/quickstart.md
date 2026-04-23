# Quickstart: YOLO Dataset Pipeline

## Prerequisites
- Run the monorepo `/init` flow if this is a fresh clone or worktree.
- Sync Python dependencies:
  - `uv --directory fungal-cv-qdrant sync`
- Confirm required inputs exist:
  - `Dataset/manual_labeled_data_roboflow/`
  - `Dataset/strain_to_specy.csv`

## Workflow A: Prepare relabeled dataset

```bash
uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_dataset.run
```

Expected outputs:
- `Dataset/manual_labeled_data_roboflow_species/`
- `classes.txt`
- `dataset.yaml`
- `preparation_summary.csv`

## Workflow B: Train YOLO segmentation normally

```bash
uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.run --dataset-root "/home/dat/dev/mycoai/Dataset/manual_labeled_data_roboflow_species"
```

Expected outputs:
- `train_test_manifest.json`
- `results/cross_validation_yolo/segmentation/segmentation_split_metadata.json`
- `results/cross_validation_yolo/segmentation/segmentation_metrics.json`
- `results/cross_validation_yolo/segmentation/yolo_segmentation/`
- `weights/segmentation/yolo_segmentation_best.pt`

## Workflow C: Materialize 5-fold classification datasets

```bash
uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_cross_validation.run --dataset-root "/home/dat/dev/mycoai/Dataset/manual_labeled_data_roboflow_species" --folds 5
```

Expected outputs:
- `Dataset/manual_labeled_data_roboflow_species_cv/fold_0` ... `fold_4`
- `results/cross_validation_yolo/folds.csv`
- `results/cross_validation_yolo/metrics.csv`
- `results/cross_validation_yolo/fold_accuracy.png`

## Workflow D: Generate augmentation debug preview

Planned command surface:
- choose one source crop or image
- apply the configured augmentation policy
- write a preview grid before long training runs

Expected outputs:
- augmentation preview image grid under `results/`

## Workflow E: Create colony crop datasets for extractor fine-tuning

Crop datasets are created automatically by the fine-tuning workflow, or can be materialized first by calling the crop helpers from `src.experiments.finetune_dl.crop_dataset`.

Expected outputs:
- crop dataset root(s) such as `Dataset/manual_labeled_data_roboflow_species_crops/`
- `crop_assignment.csv`
- `results/cross_validation_yolo/crop_dataset_summary.json`

## Workflow F: Fine-tune extractor backbones on crop datasets

```bash
uv --directory fungal-cv-qdrant run python -m src.experiments.finetune_dl.train_yolo_crops --dataset-root "/home/dat/dev/mycoai/Dataset/manual_labeled_data_roboflow_species" --model-name ResNet50
```

Expected outputs:
- `weights/yolo_finetuned/ResNet50_finetuned.pth`
- `weights/yolo_finetuned/ResNet50_classifier_checkpoint.pth`
- `results/cross_validation_yolo/finetune/ResNet50_history.json`
- `results/cross_validation_yolo/finetune/ResNet50_summary.json`

## Verification Commands
- `uv --directory fungal-cv-qdrant run pytest tests/test_yolo_dataset_pipeline.py tests/test_yolo_cross_validation.py tests/test_yolo_visualization.py tests/test_yolo_crop_dataset.py`
- `uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_dataset.run`
- `uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_segmentation.run --dataset-root "/home/dat/dev/mycoai/Dataset/manual_labeled_data_roboflow_species" --epochs 50`
- `uv --directory fungal-cv-qdrant run python -m src.experiments.yolo_cross_validation.run`
- `uv --directory fungal-cv-qdrant run python -m src.experiments.finetune_dl.train_yolo_crops --dataset-root "/home/dat/dev/mycoai/Dataset/manual_labeled_data_roboflow_species" --model-name ResNet50`

## Expected Deliverables
- relabeled species dataset for segmentation
- 5 fold classification datasets with `train/` and `test/`
- colony crop datasets for extractor training
- augmentation debug preview artifacts
- cross-validation CSVs and plots under `results/cross_validation_yolo/`
- backbone-only fine-tuned weights usable by `feature_extractors.py`
