# Technical Spec: Training Pipeline

## Overview

Design the model training and re-indexing pipeline. The backend triggers
training jobs as Celery tasks, monitors progress, and deploys updated
models to Qdrant.

---

## Training Types

| Type | What it does | Trigger |
|------|-------------|---------|
| **Re-index** | Re-extract features for all active segments, upsert to Qdrant | Adding new images, updating labels, archiving data |
| **Fine-tune** | Fine-tune feature extractor neural network weights | Many new images (>50), significant label corrections |
| **Full retrain** | Fine-tune + re-index + evaluate | Major database expansion (>200 images) |

---

## Re-index Pipeline

    1. Data owner clicks "Re-index" on training dashboard
    2. Backend counts affected segments (new, modified, archived)
    3. Pre-flight summary shown to owner
    4. Owner confirms -> POST /api/v1/training/trigger { type: "reindex" }
    5. Celery task starts:
       a. For each active segment (non-archived):
          - Extract features (all extractors: EfficientNetB1, ResNet50...)
          - Upsert named vectors to Qdrant
          - Update qdrant_index_state (last_updated, is_active=TRUE)
       b. For archived segments:
          - Delete Qdrant points
          - Update qdrant_index_state (is_active=FALSE)
       c. Progress: (processed / total) segments
    6. On completion:
       - Update model_version
       - Log completion to training_jobs
       - Notify data owner

---

## Fine-tune Pipeline

    1. Data owner clicks "Fine-tune model"
    2. Pre-flight: count training images, show estimated time
    3. Owner confirms -> POST /api/v1/training/trigger { type: "finetune" }
    4. Celery task:
       a. Prepare dataset: active segment images, stratified by species
       b. Run fungal-cv-qdrant fine-tuning script
          - Load base model (EfficientNetB1, ImageNet weights)
          - Train classification head for N species
          - Save .pth weights to weights/
       c. Evaluate on held-out split, record F1 score
       d. Stage model (not auto-deployed)
    5. Owner reviews evaluation metrics
    6. Owner clicks "Deploy" -> re-index with new model

---

## Model Versioning

**[DECISION: Model versioning strategy]**

Choices:
- A) **Semantic versioning: v{major}.{minor}.{patch}** — major=new
  architecture, minor=new training, patch=re-index. **(Recommended)**
- B) Timestamp-based: 2025-05-11-1430
- C) Auto-increment integer: model_1, model_2...

**Version storage:**

    training_jobs.model_version = "v3.2.1"
    Previous model weights kept in weights/archive/v3.2.0/

---

## Rollback

**[DECISION: Rollback mechanism]**

Choices:
- A) **Keep previous model weights + re-index with previous model** —
  safest, requires storage for old weights. Re-index is deterministic
  given model weights. **(Recommended)**
- B) Keep previous Qdrant collection snapshot — Qdrant snapshots API
- C) No rollback — trust the evaluation metrics, deploy only good models

**Rollback flow:**

    1. Owner clicks "Rollback" on training dashboard
    2. Select previous version from dropdown
    3. Confirm -> POST /api/v1/training/rollback { version: "v3.2.0" }
    4. Celery task: re-index all segments with v3.2.0 weights
    5. Update model_version

---

## Deployment Strategy

**[DECISION: When to deploy new models]**

Choices:
- A) **Manual review + deploy** — training completes, owner reviews
  metrics, clicks Deploy. Safest, most control. **(Recommended)**
- B) Auto-deploy on threshold — if F1 > previous best, auto-deploy
- C) Staged deploy — deploy new model alongside old, A/B test for a week

**Deploy process:**

    1. New model trained + saved to weights/
    2. Owner sees: "Model v3.3.0 ready for review"
       - F1: 0.92 (vs current 0.89)
       - Confusion matrix preview
       - Per-species accuracy breakdown
    3. Owner reviews -> clicks "Deploy v3.3.0"
    4. Backend triggers re-index with new model
    5. All new queries use v3.3.0 from this point
    6. Previous model v3.2.0 weights archived

---

## A/B Evaluation

**[DECISION: A/B evaluation support]**

Choices:
- A) **Run evaluation on held-out set, show comparison table** — old vs
  new F1, per-species, confusion matrix diff. No live A/B traffic
  splitting. **(Recommended for MVP)**
- B) Live traffic split — 50% queries use old model, 50% new. Compare
  real-world accuracy. Complex, requires feedback integration.
- C) No A/B — just deploy and monitor overall accuracy over time

---

## GPU Requirements

**[DECISION: GPU for training]**

Choices:
- A) **Vast.ai GPU instance (on-demand)** — already in monorepo workflow.
  Spin up instance, run training, download weights, destroy instance.
  Cost: ~$0.50-2/hr. **(Recommended)**
- B) Local GPU (if available) — fastest iteration, no cost
- C) Hugging Face Jobs — managed training, more expensive
- D) CPU-only — slow but works, GIL-bound

**Re-indexing does NOT need GPU:** feature extraction with pre-trained
models can run on CPU (slower but functional). Fine-tuning requires GPU.

---

## Monitoring

| Metric | How |
|--------|-----|
| Training progress | Celery task state + progress JSON |
| Training logs | Streaming output to training_jobs.log |
| GPU utilization | Vast.ai monitoring API |
| Training cost | Track GPU hours per job |
| Model accuracy over time | Track F1 per version in training_jobs |

---

## Scheduling

**[DECISION: Scheduled retraining]**

Choices:
- A) **Manual only** — data owner triggers when ready. Simplest.
  **(Recommended for MVP)**
- B) Scheduled (e.g., weekly) — automatic re-index for new data
- C) Threshold-based — auto-trigger when N feedback accepted or N images
  added
