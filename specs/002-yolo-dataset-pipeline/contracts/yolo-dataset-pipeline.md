# Contract: YOLO Dataset Pipeline CLI and Artifacts

## Purpose
Define the expected artifacts and execution surfaces for species-labeled dataset preparation, segmentation train/test, classification fold materialization, colony-crop dataset creation, augmentation debugging, and backbone fine-tuning for extractor-compatible YOLO-derived workflows.

## 1. Dataset Preparation Contract

### Inputs
- Source dataset root: `Dataset/manual_labeled_data_roboflow/`
- Mapping CSV: `Dataset/strain_to_specy.csv`

### Behavior
- Parse `DTO_XXX-XX` from filenames
- Normalize identifiers to match the mapping CSV
- Rewrite segmentation label class IDs from generic colony to mapped species IDs
- Preserve source images and label geometry

### Required Outputs
- Relabeled dataset root under `Dataset/manual_labeled_data_roboflow_species/`
- `classes.txt`
- `dataset.yaml`
- `preparation_summary.csv`

## 2. Segmentation Train/Test Contract

### Inputs
- Relabeled dataset root
- deterministic split configuration

### Behavior
- Produce exactly two partitions: train and test
- Do not create a validation partition
- Train YOLO segmentation normally on this dataset product
- Record split seed and membership summary

### Required Outputs
- `train_test_manifest.json`
- segmentation training metrics summary
- report-ready metadata

## 3. Classification Fold Dataset Contract

### Inputs
- Relabeled dataset root
- normalized strain/species mapping
- requested fold count

### Behavior
- Materialize one dataset root per fold under `Dataset/manual_labeled_data_roboflow_species_cv/fold_*`
- Each fold contains `train/` and `test/` only
- Each species contributes one selected test strain per fold
- Species with too few strains may use round-robin strain reuse when required by the configured fold count
- Fold train/test assignment MUST ignore Roboflow `train/valid/test` folder membership

### Required Outputs
- `classes.txt`
- `dataset.yaml`
- `fold_assignment.csv`
- aggregate fold summary under `results/cross_validation_yolo/`

## 4. Colony Crop Dataset Contract

### Inputs
- Segmentation labels or generated masks/bounding regions
- parent segmentation or fold dataset root

### Behavior
- Create colony-centric crops from labeled regions before extractor fine-tuning
- Preserve parent train/test membership in the crop dataset
- Support crop jitter inside the colony region without crossing far outside the object

### Required Outputs
- crop dataset root with train/test structure
- crop assignment metadata
- mapping between crop files and source images/regions

## 5. Augmentation Debug Contract

### Inputs
- one source image or crop
- configured augmentation policy

### Behavior
- Render a visual grid of augmented outputs before large training runs
- Reflect the same transform policy used during training

### Required Outputs
- preview image grid under `results/` or another documented debug path
- augmentation metadata naming the transforms used

## 6. Backbone Fine-Tuning Contract

### Inputs
- Classification fold crop datasets and/or segmentation crop datasets
- selected backbone name
- training hyperparameters

### Behavior
- Attach a classifier head for supervised training
- Unfreeze the last backbone stage before the classifier head
- Save training history and checkpoint artifacts
- Export backbone-only weights without the classifier head for downstream feature extraction

### Required Outputs
- backbone-only weights under `weights/`
- training history JSON under `weights/` or `results/`
- optional classifier checkpoint if needed for debugging
- metadata linking weights to the fold or split used for training

## 7. Extractor Compatibility Contract

### Behavior
- Exported weights MUST load through `src/experiments/feature_extraction/feature_extractors.py`
- Extractor inference MUST remove or bypass the classifier head
- Resulting model output MUST be embedding features, not class logits

### Required Outputs
- extractor-compatible `.pth` files named to match the expected extractor classes

## 8. Reporting Contract

### Required Sections
- dataset provenance and mapping source
- segmentation dataset and train/test summary
- classification fold dataset summary
- crop dataset creation strategy for retrieval fine-tuning
- augmentation policy and debug preview evidence
- backbone fine-tuning settings and exported weight paths
- round-robin behavior notes when species have fewer strains than fold count
- analysis figures and referenced CSV artifacts
