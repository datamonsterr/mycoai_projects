## Context

Currently, `Image.data_update_status` tracks per-item Qdrant index staleness. The Dashboard combines index health and retraining recommendation into one card with a single `external_retraining_recommended` boolean. The `TrainingJob` model exists but training is never auto-triggered — the system only shows guidance. This change formalizes the split: re-index tracking stays per-item, retraining tracking moves to an aggregate counter with threshold-based warning.

No existing specs directory. Backend uses FastAPI + SQLAlchemy async. Frontend is React 19 + Vite with mock data. Both repos are in this monorepo.

## Goals / Non-Goals

**Goals:**
- Split warning systems: per-item re-index (`data_update_status`) vs aggregate retraining counter
- Data Owner sees two independent health indicators on Dashboard
- Data Owner can download current dataset in YOLO format for external training
- Retraining warning fires based on configurable threshold, not every change
- Remove any residual auto-training trigger paths
- Zero DB migration for existing tables (add one lightweight `system_state` table)

**Non-Goals:**
- Auto-trigger retraining (explicitly removed)
- Auto-trigger re-indexing (stays manual, user decides)
- Training job orchestration (stays external)
- Model evaluation pipeline changes
- Real-time counter updates via WebSocket (polling on dashboard load is fine)

## Decisions

### D1: Retraining counter stored in `system_state` table

**Choice**: New `system_state` table with `key` (VARCHAR PK) and `value` (JSONB). Single row `key='retraining_counter'` stores `{images_added, bbox_corrections, items_archived, species_added, last_reset_at, threshold}`.

**Rationale**: Avoids migration on existing tables. Incremental updates on relevant actions (O(1) writes). Simple reset on training completion. Computed aggregates from Image/AuditLog would require expensive scans on every dashboard load.

**Alternatives considered**:
- Compute from Image timestamps → expensive queries, no explicit "acknowledged" boundary
- Store in TrainingJob.changes_since_last → couples counter to job lifecycle, harder to reset
- Add columns to Image → per-row migration, dual-write complexity

### D2: YOLO export endpoint streams from DB, no pre-generation

**Choice**: `GET /api/v1/dataset/export/yolo?species_id=...&media_id=...&status=current` streams a zip. Backend queries active Images + Segments, maps species to class indices, writes YOLO label files per image, streams as `StreamingResponse`.

**Rationale**: Always current. No stale cached exports. Filtering at query time. Zip streaming keeps memory low.

**Alternatives considered**:
- Pre-generated export via background task → stale, needs invalidation
- rclone sync to Google Drive → adds infrastructure dependency, not interactive
- CSV-only export → not useful for YOLO training

### D3: Dashboard splits into two Card components

**Choice**: Replace single "Index Status" card with:
1. "Qdrant Index Health" card — shows `data_update_status` counts, `items_updated`/`items_archived`/`feedback_accepted`, "Re-index Qdrant" button
2. "Model Training Status" card — shows retraining counter breakdown, threshold progress bar, "Export YOLO Dataset" link, "Upload Candidate Model" link

**Rationale**: Distinct user actions (re-index vs export-and-train) need distinct UI surfaces. Reduces confusion about what "needs attention" means.

### D4: `IndexStatusResponse` split into `reindex` and `retraining` sub-objects

**Choice**:
```json
{
  "reindex": {
    "status": "current|needs_reindex",
    "items_updated": 12,
    "items_archived": 3,
    "feedback_accepted": 5,
    "contributions_accepted": 4
  },
  "retraining": {
    "counter": {
      "images_added": 24,
      "bbox_corrections": 7,
      "items_archived": 5,
      "species_added": 2
    },
    "threshold": 20,
    "warning_active": true,
    "last_training_completed_at": "2025-05-15T..."
  },
  "current_model_version": "efficientnet-b1-v3"
}
```

Backward-incompatible but no consumers outside this monorepo. Frontend mock data and types updated in lockstep.

### D5: Actions that increment retraining counter

| Action | Counter field incremented |
|---|---|
| New image ingested (via batch/index) | `images_added` |
| Data Owner corrects bounding box | `bbox_corrections` |
| Image archived | `items_archived` |
| New Species created | `species_added` |
| Species/strain rename (metadata only) | _none_ |
| Wrong-prediction feedback accepted (species corrected) | _none_ (metadata change only) |

This distinction matches the domain rule: metadata-only changes trigger re-index, data changes trigger both re-index and retraining counter.

## Risks / Trade-offs

- **Counter reset race**: If two Data Owners acknowledge training simultaneously → last write wins but both succeed. Low risk (rare operation, single-owner teams). Mitigation: document that only one owner should acknowledge.
- **YOLO export size**: Large datasets may produce multi-GB zips. Mitigation: add `limit` query param; show estimated size in UI before download.
- **No per-image retraining flag**: Cannot query "which images need retraining" — only aggregate counter. Acceptable trade-off for simplicity. If needed later, add `training_relevant_since` timestamp column on Image.
- **Threshold tuning**: Default threshold of 20 may be wrong for small or large datasets. Mitigation: make configurable via `system_state` or env var.

## Migration Plan

1. Deploy backend first: new `system_state` table via Alembic, new `/export/yolo` endpoint, split `IndexStatusResponse`
2. Deploy frontend: updated types, split Dashboard cards, YOLO export button in Dataset Browser
3. No data migration needed — counter starts at 0 on first deploy
4. Rollback: revert frontend + backend. `system_state` table is additive, no data loss on rollback.

## Open Questions

- Q: Should threshold be per-species or global? → A: Global for MVP. Per-species adds complexity without clear benefit yet.
- Q: Should YOLO export include archived images? → A: No. Only `data_update_status != 'archived'`. Archived images are excluded from training.
