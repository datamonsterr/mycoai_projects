# Data Model: YOLO Dataset Pipeline

## Entities

### 1. Strain Mapping Record
- **Fields**:
  - `strain_id`: canonical normalized strain identifier
  - `species_name`: mapped species label
  - `test_flag`: legacy flag from the source CSV
- **Validation Rules**:
  - the identifier must normalize from DTO filenames and the mapping CSV consistently
  - `species_name` must be non-empty for trainable samples

### 2. Derived Species-Labeled Sample
- **Fields**:
  - `image_path`: copied image path in the relabeled dataset
  - `label_path`: YOLO segmentation polygon label rewritten with species class ID
  - `strain_id`: source strain identifier
  - `species_name`: mapped species label
  - `source_split_name`: original Roboflow split for provenance only
- **Validation Rules**:
  - annotation geometry must remain unchanged after relabeling
  - class IDs must come from the generated species manifest

### 3. Segmentation Train/Test Manifest
- **Fields**:
  - `dataset_root`: relabeled dataset root
  - `seed`: deterministic split seed
  - `train`: list of training sample paths
  - `test`: list of test sample paths
- **Validation Rules**:
  - no validation partition exists
  - train and test sample lists are disjoint

### 4. Classification Fold Dataset
- **Fields**:
  - `fold_id`: fold identifier
  - `fold_root`: dataset root for one fold under `Dataset/manual_labeled_data_roboflow_species_cv/`
  - `train/images`: all non-held-out samples for the fold
  - `test/images`: held-out strain samples for the fold
  - `fold_assignment.csv`: per-image assignment summary
  - `round_robin_species`: species that reuse strains across folds
- **Validation Rules**:
  - each species contributes one selected test strain in a fold
  - a fold’s held-out strain must not appear in that fold’s training split

### 5. Colony Crop Dataset
- **Fields**:
  - `crop_dataset_root`: dataset root for cropped colony images
  - `source_dataset_root`: source segmentation dataset or fold dataset used to create crops
  - `crop_image_path`: saved crop path
  - `crop_label`: species label for the crop
  - `bbox_or_mask_source`: source region used to create the crop
  - `split_name`: train or test assignment inherited from the parent dataset
- **Validation Rules**:
  - crops must stay inside the colony region or a controlled jitter around it
  - train/test split must match the parent fold or segmentation manifest

### 6. Augmentation Debug Artifact
- **Fields**:
  - `input_image_path`: source crop or image used for augmentation preview
  - `augmentation_policy_name`: configured augmentation set
  - `preview_image_path`: rendered grid output path
  - `transform_names`: transforms used in the preview
- **Validation Rules**:
  - the preview must reflect the actual training-time augmentation configuration
  - transforms should preserve biologically plausible colony appearance

### 7. Fine-Tuning Run
- **Fields**:
  - `model_name`: backbone name (`ResNet50`, `MobileNetV2`, `EfficientNetB1`)
  - `fold_id`: optional fold identifier for classification runs
  - `device`: CPU or CUDA device used for training
  - `history_path`: saved training history JSON
  - `backbone_weights_path`: saved backbone-only weights for extractor loading
  - `classifier_checkpoint_path`: optional full classification checkpoint
  - `crop_dataset_root`: crop dataset used for training
- **Validation Rules**:
  - training attaches a classifier head temporarily
  - exported backbone weights must omit the classification head for extractor use
  - the last backbone stage before the classifier must be unfrozen during fine-tuning

### 8. Extractor-Compatible Weights
- **Fields**:
  - `weights_path`: saved `.pth` file under `weights/`
  - `extractor_name`: matching extractor contract name
  - `backbone_type`: ResNet50, MobileNetV2, EfficientNetB1, or similar
  - `feature_dim`: embedding dimension exposed after classifier removal
- **Validation Rules**:
  - weights must load into `feature_extractors.py` with classifier removal intact
  - saved state should remain usable for downstream retrieval embedding extraction

### 9. Cross-Validation Summary Artifact
- **Fields**:
  - `folds_csv`: held-out strain summary
  - `metrics_csv`: fold-level metrics and warnings
  - `visualization_paths`: generated plots
  - `fold_dataset_roots`: per-fold dataset locations
- **Validation Rules**:
  - summaries must reconcile with per-fold train/test assignments
  - warnings must record any round-robin reuse behavior

### 10. YOLO Experiment Report
- **Fields**:
  - `report_path`: markdown or report artifact path
  - `segmentation_section`: segmentation dataset, split, and training outputs
  - `classification_section`: fold datasets, crop datasets, fine-tuning outputs, and extractor compatibility notes
  - `artifact_index`: referenced CSVs, fold roots, crop roots, weights, and figures
- **Validation Rules**:
  - must explicitly distinguish segmentation train/test from classification fold datasets
  - must document that fine-tuned backbones are exported without the classifier head for feature extraction
