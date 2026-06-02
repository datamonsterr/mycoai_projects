# Feature Spec: Model and Index Maintenance

## Overview

Data Owners maintain the Qdrant index in-system and manage deep feature-extractor model versions through external retraining guidance plus Candidate Model assessment. The system does not trigger deep feature-extractor retraining.

## User Stories

### 1. View Model and Index Status

**As a** Data Owner
**I want to** see current model and Qdrant index status
**So that I** know whether retrieval reflects current reference data

**Behavior:**
- Dashboard widget shows:
  - Current model version
  - Current Qdrant index status
  - Count of data items with `updated_requires_reindex`
  - Count of archived/restored records since last index update
  - Count of accepted feedback/contributions since last index update
  - Latest evaluation metrics

### 2. Re-index Qdrant

**As a** Data Owner
**I want to** trigger Qdrant re-indexing
**So that** metadata, archive, restore, and accepted feedback changes affect retrieval

**Behavior:**
- Data Owner reviews pre-flight summary
- Data Owner triggers in-system Qdrant re-index
- System re-extracts features for active changed segments and updates Qdrant points
- Archived items are excluded from Qdrant retrieval
- System updates Data Update Status to `current` after successful re-index
- Audit log records re-index action

### 3. Review External Retraining Guidance

**As a** Data Owner
**I want to** be warned when many reference-data changes accumulate
**So that I** know when deep feature-extractor retraining may be needed

**Behavior:**
- System shows warning when accumulated reference-data changes exceed configured threshold
- Warning includes changed/accepted/archived counts
- System provides Python guidance to:
  1. Download active dataset
  2. Retrain feature extractor externally
  3. Upload Candidate Model
- No in-system deep retraining trigger is available

### 4. Version and Assess Candidate Model

**As a** Data Owner
**I want to** upload and assess a Candidate Model
**So that** I can compare it against the current model before promotion

**Behavior:**
- Data Owner uploads Candidate Model artifact
- System runs fixed evaluation set
- System compares Candidate Model metrics against current model metrics
- Data Owner manually promotes or rejects Candidate Model
- No auto-promotion occurs
- Previous model version remains available for comparison/rollback planning

## Key Design Decisions

### What re-indexing means

1. Feature re-extraction for active segment images using current model
2. Qdrant point upsert/update for active data
3. Qdrant exclusion/removal for archived data

### What retraining means

Deep feature-extractor retraining changes model weights. It is performed outside the system by Data Owner using provided Python guidance, then reuploaded as a Candidate Model.

### When re-index vs retrain?

| Action | In-system? | When needed |
|--------|------------|-------------|
| Qdrant re-index | Yes | Add/index data, edit metadata/boxes, archive/restore, accepted feedback |
| Deep feature-extractor retrain | No | Many new images, significant label/media changes, degraded evaluation |
| Candidate Model assessment | Yes | After external retraining and upload |

## Data Contract

**Index/model status:**

    {
      "current_model_version": "string",
      "qdrant_index_status": "current | needs_reindex | reindexing | failed",
      "changes_since_last_index": {
        "items_updated": 12,
        "items_archived": 3,
        "feedback_accepted": 5,
        "contributions_accepted": 4
      },
      "external_retraining_recommended": true
    }

**Candidate model evaluation:**

    {
      "candidate_model_id": "uuid",
      "status": "uploaded | evaluating | accepted | rejected",
      "current_metrics": {"f1": 0.89},
      "candidate_metrics": {"f1": 0.92},
      "evaluation_set_id": "fixed-evaluation-set"
    }

## Acceptance Criteria

- [ ] Dashboard shows current model and Qdrant index status
- [ ] Data Owner can trigger Qdrant re-indexing in-system
- [ ] Re-index pre-flight summary shows affected active/archived/updated data counts
- [ ] Successful re-index marks affected data `current`
- [ ] System warns when deep feature-extractor retraining is recommended
- [ ] System provides Python guidance for dataset download, external retraining, and model reupload
- [ ] No in-system deep retraining trigger exists
- [ ] Data Owner can upload Candidate Model
- [ ] Candidate Model is evaluated against fixed evaluation set
- [ ] Data Owner manually promotes or rejects Candidate Model
- [ ] Audit log records re-indexing and model promotion/rejection

## Dependencies

- 05-feedback-pipeline.md (accepted feedback/contributions)
- 06-data-management.md (data changes requiring re-index)
- 08-roles-and-permissions.md (Data Owner permissions)
- ../SRS.md UC-008
