# Feature Spec: Training Observation

## Overview

Data owners can monitor and trigger deep learning model training jobs.
The system provides async job status, progress tracking, and configurable
training triggers.

## User Stories

### 1. View Training Status

**As a** data owner
**I want to** see the status of model training jobs
**So that I** know when updated models are ready

**Behavior:**
- Dashboard widget showing:
  - Current model version (e.g. "EfficientNetB1 finetuned v3")
  - Last training date
  - Number of strains in training set
  - Model accuracy (F1 score from latest evaluation)
- Training history table:
  - Job ID, start time, end time, duration
  - Status: pending, running, completed, failed
  - Changes: "N strains added, M strains removed since last training"

### 2. Trigger Retraining

**As a** data owner
**I want to** manually trigger model retraining
**So that I** incorporate new data and corrections

**Behavior:**
- "Retrain" button on the training dashboard
- Pre-flight check:
  - "N new strains added since last train"
  - "M strains archived since last train"
  - "P feedback corrections accepted since last train"
  - "Estimated training time: ~X hours on current hardware"
- Confirmation dialog before starting
- Only one training job can be running at a time
- If job is already running, show progress instead

### 3. Training Progress

**As a** data owner
**I want to** monitor training progress in real-time
**So that I** know when to expect updated models

**Behavior:**
- Progress bar with:
  - Current stage (data prep, feature extraction, training epochs,
    evaluation)
  - Epoch X of Y
  - Current loss / accuracy
  - Estimated time remaining
- Training log (streaming terminal output)
- Cancel button (graceful shutdown at end of current epoch)
- Email/webhook notification on completion or failure

### 4. Model Deployment

**As a** data owner
**I want to** deploy a newly trained model
**So that I** can use improved accuracy for queries

**Behavior:**
- After training completes, model is staged (not auto-deployed)
- Data owner reviews evaluation metrics
- "Deploy" button replaces current Qdrant index with new features
- Rollback: keep previous model version, revert with one click
- A/B evaluation: compare old vs new model on a validation set

## Key Design Decisions

### What retraining means

For this system, "retraining" means:

1. **Feature re-extraction**: Run all feature extractors on all active
   (non-archived) segment images
2. **Qdrant re-indexing**: Upsert all feature vectors into Qdrant,
   replacing existing points for updated strains
3. **Deep model fine-tuning** (optional, triggered separately):
   - Fine-tune feature extractors (ResNet50, EfficientNetB1, etc.)
   - Only needed when adding many new images or correcting labels
   - Much heavier operation than re-indexing

### When full retraining vs re-indexing?

| Action | What it does | When needed |
|--------|-------------|-------------|
| Re-index into Qdrant | Re-extract features, upsert points | Add new images, update labels, archive data |
| Fine-tune feature extractor | Train neural network weights | Many new images added, significant data changes |
| Full retrain | Fine-tune + re-index | Major database expansion |

### What data owners need to know

- **High**: Whether models are up to date with current database
- **High**: Training progress and completion
- **Medium**: Model accuracy metrics
- **Low**: Individual epoch loss values (available but not primary UI)

## Data Contract

**Training job status:**

    {
      "job_id": "uuid",
      "job_type": "reindex | finetune | full_retrain",
      "status": "pending | running | completed | failed | cancelled",
      "progress": {
        "stage": "preparing | extracting | training | evaluating | indexing",
        "current": 15,
        "total": 50,
        "epoch": 3,
        "current_loss": 0.023,
        "current_accuracy": 0.87
      },
      "trigger": "manual | scheduled | feedback_accepted",
      "changes_since_last": {
        "strains_added": 12,
        "strains_archived": 3,
        "feedback_accepted": 5
      },
      "started_at": "ISO8601",
      "completed_at": "ISO8601 | null",
      "estimated_completion": "ISO8601 | null"
    }

## Acceptance Criteria

- [ ] Training status dashboard with current model info
- [ ] Training history table
- [ ] Manual retrain trigger with pre-flight summary
- [ ] Real-time progress bar with stage/epoch/loss
- [ ] Cancel training with graceful shutdown
- [ ] Completion notification (in-app + optional email)
- [ ] Staged deployment with review step
- [ ] Rollback to previous model version
- [ ] A/B comparison of old vs new model

## Dependencies

- 05-feedback-pipeline.md (accepted feedback triggers re-indexing)
- 06-data-management.md (CRUD operations trigger retraining)
- Consumes: fungal-cv-qdrant feature extraction, DNN training scripts,
  Qdrant indexing utilities
