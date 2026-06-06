# Technical Spec: Model and Index Maintenance

## Overview

Backend supports Qdrant re-indexing and Candidate Model assessment.

**Use case reference**: UC-MODEL-01.

Deep feature-extractor retraining is not triggered in-system; Data Owner receives Python guidance for external retraining and reuploads the resulting model as a Candidate Model.

---

## Maintenance Types

| Type | In-system | What it does | Trigger | Data Owner action |
|------|----------|--------------|---------|-------------------|
| Qdrant re-index | Yes | Re-extract features for active changed segments and upsert/update Qdrant points; exclude archived data | Data adds, metadata edits, bbox edits, archive/restore, accepted feedback | Open Maintain Model dashboard, review pre-flight summary, confirm re-index |
| External retraining guidance | Yes (guidance only) | Shows dataset download/retrain/reupload instructions | Many reference-data changes accumulated | Review guidance, run external Python workflow, reupload Candidate Model |
| Deep feature-extractor retraining | No | Trains neural network weights outside system | Data Owner runs external Python workflow | (external only) |
| Candidate Model assessment | Yes | Evaluates uploaded model on fixed set and compares with current model | Candidate Model upload | Upload artifact, review evaluation report, manually promote or reject |

---

## Qdrant Re-index Pipeline

    1. Data Owner opens Maintain Model and Index dashboard
    2. Backend counts affected data:
       - updated_requires_reindex
       - archived since last index
       - restored since last index
       - accepted feedback/contributions since last index
    3. System shows pre-flight summary
    4. Data Owner confirms re-index
    5. Backend task starts:
       a. For each active changed segment:
          - Extract features with current model
          - Upsert named vectors to Qdrant
          - Mark Data Update Status current
       b. For archived segments:
          - Exclude/remove Qdrant points
          - Keep archive state
       c. Record progress
    6. On completion:
       - Update index status
       - Log audit event
       - Notify Data Owner

---

## External Retraining Guidance

When accumulated reference-data changes exceed configured threshold, system shows a warning and Python guidance. Guidance covers:

1. Download active dataset
2. Run external feature-extractor retraining
3. Produce model artifact with version metadata
4. Reupload artifact as Candidate Model

No endpoint starts deep model retraining.

---

## Candidate Model Assessment

    1. Data Owner uploads Candidate Model artifact
    2. Backend validates model metadata and compatibility
    3. Backend evaluates Candidate Model on fixed evaluation set
    4. Backend compares Candidate Model metrics to current model metrics
    5. Data Owner reviews report
    6. Data Owner promotes or rejects Candidate Model
    7. Promotion updates active model version and may require Qdrant re-indexing

---

## Model Versioning

**Decision: Semantic versioning `v{major}.{minor}.{patch}`.**

| Version part | Meaning |
|---|---|
| major | New architecture or incompatible feature space |
| minor | New externally trained Candidate Model promoted |
| patch | Qdrant re-index or metadata-only index refresh |

Version storage:

    model_versions.version = "v3.2.1"
    model_versions.status = "active | candidate | rejected | archived"

---

## Promotion Strategy

**Decision: Manual review + promote.**

Candidate Model is never auto-promoted. Data Owner must compare metrics and explicitly promote or reject.

---

## Evaluation Support

**Decision: Fixed evaluation set comparison for MVP.**

Show:
- Current vs Candidate F1
- Per-Species performance where available
- Confusion matrix preview where available
- Evaluation set identifier/version

No live traffic A/B split for MVP.

---

## Rollback

Recommended mechanism: keep previous model weights and re-index with previous model when rollback is required. Rollback is a future operational action, not automatic promotion logic.

---

## API Shape

    POST /api/v1/index/reindex
    Body: { scope: "changed | full_active" }

    GET /api/v1/index/status
    Response: {
      qdrant_index_status,
      changes_since_last_index,
      external_retraining_recommended
    }

    POST /api/v1/models/candidates
    Body: multipart model artifact + metadata

    POST /api/v1/models/candidates/{id}/evaluate

    POST /api/v1/models/candidates/{id}/promote

    POST /api/v1/models/candidates/{id}/reject

---

## Monitoring

| Metric | How |
|--------|-----|
| Re-index progress | Task state + progress JSON |
| Index freshness | Data Update Status counts |
| External retraining recommendation | Changed-data thresholds |
| Candidate Model accuracy | Fixed evaluation report |
| Model version history | model_versions table |

---

## Resolved Decisions

1. Qdrant re-indexing is in-system.
2. Deep feature-extractor retraining is external/manual.
3. System provides Python retraining guidance instead of training trigger.
4. Candidate Model assessment uses fixed evaluation set.
5. Candidate Model promotion is manual only.
