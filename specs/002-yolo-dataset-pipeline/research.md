# Research: YOLO Dataset Pipeline

## Decision 1: Keep the implementation inside `fungal-cv-qdrant` and shared root data paths
- **Decision**: Implement dataset relabeling, segmentation split materialization, species classification fold materialization, augmentation debugging, crop dataset creation, backbone fine-tuning, and report generation within `fungal-cv-qdrant`, while reading from root-level `Dataset/` and writing to root-level `results/` and `weights/`.
- **Rationale**: The constitution assigns dataset preparation, experiment execution, feature extraction, and report generation to `fungal-cv-qdrant`.
- **Alternatives considered**:
  - Move training orchestration to the monorepo root: rejected because it would blur repo ownership.
  - Push training logic into backend/frontend repos: rejected because this remains experiment-side work.

## Decision 2: Preserve two dataset products, one for segmentation and one for classification folds
- **Decision**: Keep `Dataset/manual_labeled_data_roboflow_species/` as the relabeled source product for segmentation, use a train/test manifest for segmentation, and materialize dedicated classification fold datasets under `Dataset/manual_labeled_data_roboflow_species_cv/fold_*`.
- **Rationale**: Segmentation and retrieval-style classification use different split rules. Keeping both products explicit avoids hidden dependence on Roboflow folder membership.
- **Alternatives considered**:
  - Reuse one folder layout for both segmentation and classification: rejected because the classification requirement explicitly ignores Roboflow `train/valid/test`.

## Decision 3: Use round-robin strain selection for 5-fold classification datasets
- **Decision**: Build 5 folds by cycling strains per species with round-robin when a species has fewer than 5 distinct strains.
- **Rationale**: The latest user requirement is to keep 5 folds rather than exclude species with low strain counts.
- **Alternatives considered**:
  - Exclude species with too few strains: rejected by the user.
  - Reduce the fold count: rejected by the user.

## Decision 4: Fine-tune extractor backbones on colony crops, not raw detector outputs
- **Decision**: For retrieval/extractor fine-tuning, create a colony-crop dataset from segmentation labels or predicted masks/bounding boxes, and train the backbone on those crops rather than training directly on object detector outputs.
- **Rationale**: The existing `finetune_dl/` workflow is already based on segmented colony images. Retrieval combines embeddings with environment filtering and KNN aggregation; that benefits from stable colony-centric crops more than from full-image detection outputs.
- **Alternatives considered**:
  - Use detection outputs only with no crop dataset: rejected because retrieval embeddings should represent colonies, not detection heads.
  - Skip crop generation and train on whole plates: rejected because it would dilute colony-specific signal and break alignment with the current retrieval workflow.

## Decision 5: Fine-tune backbones with a temporary classifier head, then export backbone-only weights for extractors
- **Decision**: Follow the `finetune_dl/train_models.py` pattern: attach a classifier head during supervised training on the crop datasets, unfreeze the last backbone block before the classifier, then save backbone-only weights that `feature_extractors.py` can load with the classification head removed.
- **Rationale**: The extractor classes already expect backbone-style weights and remove classifier layers during feature extraction. Training needs the head, retrieval does not.
- **Alternatives considered**:
  - Train and save end-to-end classification models only: rejected because downstream use needs feature vectors, not logits.
  - Freeze the full backbone and train only the head: rejected because the user explicitly asked to unfreeze the layer before classification.

## Decision 6: Add augmentation debugging before large training runs
- **Decision**: Implement an augmentation debug script that takes one image/crop and writes a grid of augmented variants so augmentation policies can be visually inspected before training.
- **Rationale**: The user explicitly asked to validate augmentation visually first. This reduces the risk of training on biologically implausible transformations.
- **Alternatives considered**:
  - Tune augmentations only by code review: rejected because visual validation is more reliable for image workflows.

## Decision 7: Use colony-safe augmentations tailored to fungal plate imagery
- **Decision**: Prefer small geometric transforms, brightness/contrast/color perturbations, mild blur/noise/compression, crop jitter inside the colony bounding region, and optional circular/object-interior masking or cutout.
- **Rationale**: These preserve colony identity while simulating acquisition variation. Heavy perspective warps or unrealistic deformations would likely hurt retrieval quality.
- **Alternatives considered**:
  - Strong perspective or elastic transforms: rejected because they distort colony morphology unnaturally.

## Decision 8: Train YOLO segmentation normally
- **Decision**: Keep YOLO segmentation training as a standard segmentation training workflow on the relabeled species dataset and its train/test manifest.
- **Rationale**: The user explicitly requested normal segmentation training, while the retrieval-specific complexity belongs in the crop-based fine-tuning flow instead.
- **Alternatives considered**:
  - Force segmentation and retrieval into one combined training loop: rejected because they solve different problems and need different outputs.

## Decision 9: CPU-only execution is acceptable for planning, but training workflow must remain GPU-aware
- **Decision**: Keep training scripts device-aware and runnable on CPU, but document that practical training should prefer CUDA when available.
- **Rationale**: The current environment reports no CUDA devices, but the scripts should still remain valid in a GPU workspace.
- **Alternatives considered**:
  - Block all training unless CUDA exists: rejected because it would prevent basic validation in CPU-only environments.

## Decision 10: Verification should separate feature-local confidence from repo-wide legacy debt
- **Decision**: Continue to run feature-local tests and workflow commands for the new YOLO dataset/fold/training code, while explicitly recording pre-existing repo-wide black/isort/flake8/mypy issues as external blockers if they remain unrelated.
- **Rationale**: The repo currently contains significant unrelated lint/type debt, but the new feature still needs its own validation evidence.
- **Alternatives considered**:
  - Skip repo-wide checks entirely: rejected by constitution.
