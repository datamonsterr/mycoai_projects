# What I Learned: YOLO Dataset Pipeline

**Feature**: Species-labeled YOLO segmentation and crop-based extractor fine-tuning for fungal colony data
**Generated**: 2026-04-23
**Scope**: how do I run training script in Vast.ai
**Implementation status**: 27/40 tasks completed

---

## Key Decisions

### 1. Keep training inside `fungal-cv-qdrant`

**What we did**: We put both the YOLO segmentation runner in `fungal-cv-qdrant/src/experiments/yolo_segmentation/run.py` and the crop fine-tuning runner in `fungal-cv-qdrant/src/experiments/finetune_dl/train_yolo_crops.py`.

**Why**: This repo already owns experiment logic, dataset generation, and model artifacts. On Vast.ai that matters because you want one repo to contain the full training path instead of splitting logic across the monorepo.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| Move training scripts to the monorepo root | That would blur ownership and make experiment code harder to reason about. |
| Push training into backend/frontend repos | Those repos are product consumers, not the place to run model experiments. |

**When you'd choose differently**: If training became a shared platform concern across multiple repos, a root-level orchestration layer could make sense. For a single experiment pipeline, keeping it local is simpler and safer.

---

### 2. Use the relabeled YOLO dataset as the segmentation source of truth

**What we did**: Segmentation training reads `Dataset/manual_labeled_data_roboflow_species/` and expects `dataset.yaml` plus a generated `train_test_manifest.json` in `run_yolo_segmentation`.

**Why**: That keeps segmentation tied to the species-aware labels, which is the whole point of this feature. On Vast.ai, this also gives you a clean input boundary: upload or sync one prepared dataset root, then train directly from it.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| Train from the original Roboflow dataset | That would keep the generic colony class and lose the new species mapping work. |
| Recompute labels at training time | That would make runs less reproducible and harder to debug remotely. |

**When you'd choose differently**: If storage were extremely constrained, you might transform labels on the fly. That tradeoff only makes sense when compute is cheap and reproducibility pressure is low.

---

### 3. Separate segmentation training from extractor fine-tuning

**What we did**: We use `src.experiments.yolo_segmentation.run` for YOLO segmentation and `src.experiments.finetune_dl.train_yolo_crops` for classification-style backbone fine-tuning on crops.

**Why**: They solve different problems. Segmentation learns masks for colonies; fine-tuning learns embeddings or classifier-ready backbones from colony-centric crops.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| One combined training pipeline | It would mix two objectives and make debugging much harder on remote GPU machines. |
| Fine-tune directly on detector outputs | That would couple retrieval training to detection internals instead of stable crop artifacts. |

**When you'd choose differently**: If you were building a unified multitask model with clear shared gains, a combined pipeline could be worth it. For research iteration, separate pipelines are easier to operate.

---

### 4. Create crop datasets before backbone fine-tuning

**What we did**: `run_crop_finetuning` first materializes crop data with `create_crop_dataset`, then trains on `train/` and `test/` class folders.

**Why**: This keeps the training input explicit and inspectable. On Vast.ai that is valuable because remote jobs fail in annoying ways; it helps to be able to inspect the crop dataset independently from the trainer.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| Crop on the fly inside the training loop | Harder to debug, harder to cache, and harder to inspect remotely. |
| Train on full plate images | That would dilute the colony-specific signal the extractor is supposed to learn. |

**When you'd choose differently**: If preprocessing cost dominated runtime and the crop logic was already stable, online cropping might be okay. For a new research pipeline, explicit artifacts are easier to trust.

---

### 5. Export backbone-only weights after fine-tuning

**What we did**: `export_backbone_weights` strips classifier layers (`fc.` for ResNet50, `classifier.` for MobileNetV2/EfficientNetB1) and saves the remainder under `weights/yolo_finetuned/`.

**Why**: `feature_extractors.py` wants embedding backbones, not final logits. This keeps training-time supervision and inference-time feature extraction loosely coupled.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| Save only the full classifier checkpoint | That is useful for debugging but not enough for downstream feature extraction. |
| Train without a classifier head at all | Then you lose the supervised signal the user explicitly asked for. |

**When you'd choose differently**: If the downstream consumer needed class predictions instead of embeddings, exporting the full model would be more natural. For retrieval-like usage, backbone-only export is the right default.

---

### 6. Keep the scripts GPU-aware but CPU-safe

**What we did**: Both training paths use `torch.device("cuda" if torch.cuda.is_available() else "cpu")`, while the segmentation path uses Ultralytics defaults and the crop fine-tuning path explicitly moves models to the selected device.

**Why**: Vast.ai is where you expect CUDA to exist, but local development often is CPU-only. This lets you test the orchestration locally and then scale the same script remotely.

**Alternatives considered**:
| Approach | Why it wasn't chosen |
|----------|---------------------|
| Require CUDA and hard-fail locally | That would make basic verification and debugging much slower. |
| Ignore device selection entirely | That would make the training path less predictable on remote machines. |

**When you'd choose differently**: If the model were so large that CPU mode was misleading or unusable, you might hard-require CUDA. Here, CPU compatibility is still useful for smoke tests.

---

## Concepts to Know

### Artifact-first training workflow

**What it is**: Instead of hiding everything inside one trainer, you create explicit intermediate artifacts like `dataset.yaml`, `train_test_manifest.json`, crop folders, metrics JSON, and exported weights.

**Where we used it**: `src/experiments/yolo_segmentation/run.py`, `src/experiments/finetune_dl/crop_dataset.py`, `src/experiments/finetune_dl/train_yolo_crops.py`.

**Why it matters**: On Vast.ai, debugging is easier when each stage leaves a visible artifact behind. You can quickly tell whether failure came from data prep, training, or export.

---

### Train/test split as an explicit contract

**What it is**: The split is not just an implementation detail; it becomes a file-backed contract that downstream steps read and report.

**Where we used it**: `run_yolo_segmentation` writes split metadata, and the crop fine-tuning path preserves parent `train/` and `test/` membership through `create_crop_dataset`.

**Why it matters**: This avoids silent leakage. Remote training runs are expensive, so you want the split logic to be inspectable before you burn GPU hours.

---

### Temporary classifier head, permanent backbone

**What it is**: You add a classifier head only for supervised training, then remove it when exporting the reusable model.

**Where we used it**: `build_model` and `export_backbone_weights` in `src/experiments/finetune_dl/train_yolo_crops.py`.

**Why it matters**: This is a common transfer-learning pattern. It lets you use labels to shape the representation without locking your final artifact to a classification-only interface.

---

### Last-block unfreezing

**What it is**: Most pretrained layers stay frozen, while the final high-level block is trainable so the model can adapt to the fungal domain.

**Where we used it**: `build_model` in `src/experiments/finetune_dl/train_yolo_crops.py` unfreezes `layer4` for ResNet50 and the last feature block for MobileNetV2/EfficientNetB1.

**Why it matters**: It gives you a good tradeoff between adaptation and stability. On rented GPUs, that usually converges faster than full-model fine-tuning.

---

### Remote-friendly CLI design

**What it is**: Scripts accept explicit flags like `--dataset-root`, `--model-name`, `--epochs`, and `--batch-size` so they can be launched non-interactively.

**Where we used it**: `src/experiments/yolo_segmentation/run.py` and `src/experiments/finetune_dl/train_yolo_crops.py`.

**Why it matters**: Vast.ai jobs are often launched over SSH or scripts. Good CLI surfaces reduce the need to edit source code on the remote machine.

---

## Architecture Overview

This feature is organized as a pipeline with clear handoff points: dataset prep creates the species-labeled YOLO dataset, segmentation training consumes that dataset directly, cross-validation materializes fold datasets, crop generation derives classifier-ready images, and fine-tuning exports backbone-only weights for extractor reuse. On Vast.ai, that structure is helpful because each stage can be run, retried, and inspected independently.

```text
manual_labeled_data_roboflow
        ↓
yolo_dataset.run
        ↓
manual_labeled_data_roboflow_species
        ├── yolo_segmentation.run
        └── train_yolo_crops
                ↓
        crop dataset + backbone weights
```

## Glossary

| Term | Meaning |
|------|---------|
| `dataset.yaml` | The Ultralytics dataset definition file that tells YOLO where images live and what class IDs mean. |
| Backbone | The pretrained feature extractor part of the network, before the task-specific classifier head. |
| Classifier checkpoint | The full fine-tuned model state, including the classification layer used during supervised training. |
| Backbone-only weights | The exported model state with the classification head removed so it can be reused for feature extraction. |
| Crop dataset | A derived dataset of colony-centered image crops created from YOLO annotations. |
| Vast.ai | A rented remote GPU environment where you usually SSH in, sync code/data, and run long training commands non-interactively. |
