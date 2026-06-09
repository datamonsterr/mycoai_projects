## Why

Index maintenance (Qdrant re-embedding) and model retraining (deep feature extractor) share the same warning mechanism today — a single `external_retraining_recommended` flag and a combined Dashboard card. Metadata-only changes (species rename) trigger retraining warnings needlessly, while real training-relevant changes (new images, bbox corrections) are not tracked with enough granularity. The system needs to decouple these two workflows and provide explicit YOLO-format dataset export so Data Owners can train externally without confusion about what "retraining recommended" actually means.

## What Changes

- **BREAKING**: Remove implicit auto-training trigger path. The system never initiates model training. Training is always external, guided by the UI.
- Split warnings into two independent dimensions:
  - **Re-index Warning**: per-item `data_update_status` on `Image` (existing, formalized). Tracks Qdrant index staleness. Data Owner triggers re-index manually via existing button.
  - **Retraining Warning**: new aggregate `RetrainingCounter` tracking net changes since last training (new images, bbox corrections, archives, new species). Warning shown when counter exceeds configurable threshold.
- Add **YOLO Export** button to Dataset Browser. Data Owner filters dataset, downloads zip archive of images + YOLO-format label files for external training.
- Split Dashboard "Index Status" card into two independent cards: "Qdrant Index Health" and "Model Training Status".
- Update `IndexStatus` API response to return both `reindex` and `retraining` sub-objects.
- Update CONTEXT.md domain language with new terms (already done).

## Capabilities

### New Capabilities

- `yolo-dataset-export`: Backend endpoint that streams a YOLO-format zip archive of filtered active dataset images and label files. Frontend Dataset Browser gets "Export YOLO" button.
- `retraining-counter`: Aggregate counter tracking training-relevant changes (new images, bbox corrections, archived items, new species) since last model training. Configurable threshold triggers retraining warning.
- `reindex-warning`: Formalize per-item re-index tracking via `Image.data_update_status` independent of retraining. Backend sets status on metadata edits, feedback acceptance, and new data ingestion.
- `dashboard-health-split`: Split Dashboard health display into two cards — "Qdrant Index Health" (reindex metrics + trigger button) and "Model Training Status" (retraining counter, threshold bar, YOLO export guidance, Candidate Model upload link).

### Modified Capabilities

_None_ — no existing spec files. This is the first formal spec for these subsystems.

## Impact

- **Backend**: `api/index.py` (split response), `schemas/index.py` (new IndexStatus shape), `repos/feedback.py` (increment retraining counter on accepted contributions), `repos/image.py` (increment counter on bbox edits, archives), new YOLO export endpoint
- **Frontend**: `Dashboard.tsx` (split card), `ModelIndex.tsx` (update retraining guidance to reference YOLO export), `Dataset.tsx` (add YOLO export button), `lib/mock-data.ts` (update `IndexStatus` type)
- **Domain**: `CONTEXT.md` updated with Re-index Warning, Retraining Warning, Retraining Counter, YOLO Export terms
- **No DB migration needed**: retraining counter is a computed aggregate, not a new column
