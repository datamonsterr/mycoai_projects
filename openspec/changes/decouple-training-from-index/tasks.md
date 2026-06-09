## 1. Backend: Database & System State

- [ ] 1.1 Add `SystemState` model to `models/__init__.py` with `key` (String PK) and `value` (JSONB) columns
- [ ] 1.2 Create Alembic migration for `system_state` table
- [ ] 1.3 Seed initial `retraining_counter` row with zeros and default threshold (20)

## 2. Backend: Retraining Counter Repository

- [ ] 2.1 Create `repos/system_state.py` with `get_counter()` and `increment_counter(field, amount)` methods
- [ ] 2.2 Create `repos/system_state.py` with `reset_counter()` method
- [ ] 2.3 Add counter increment calls in `repos/feedback.py` on accepted contribution feedback (images_added)
- [ ] 2.4 Add counter increment calls in image repo on bbox correction (bbox_corrections) and archive (items_archived)
- [ ] 2.5 Add counter increment calls in species repo on new species creation (species_added)

## 3. Backend: Split Index Status API

- [ ] 3.1 Update `schemas/index.py`: split `IndexStatusResponse` into `ReindexStatus` + `RetrainingStatus` sub-models
- [ ] 3.2 Update `api/index.py` `get_index_status`: return split response with real counter data from `system_state`
- [ ] 3.3 Add POST `/api/v1/index/training-complete` endpoint (owner-only) that resets retraining counter

## 4. Backend: YOLO Export Endpoint

- [ ] 4.1 Add `GET /api/v1/dataset/export/yolo` route to `api/` (new file or existing dataset route) with query params: `species_id`, `media_id`, `status`
- [ ] 4.2 Implement YOLO label file generation: map species to class indices, normalize bbox coordinates to [0,1]
- [ ] 4.3 Implement streaming zip response with `images/` and `labels/` directories plus `classes.txt`
- [ ] 4.4 Add `Content-Disposition` header for browser download
- [ ] 4.5 Add owner-only guard (`CurrentOwner` dependency)

## 5. Frontend: Types & Mock Data

- [ ] 5.1 Update `IndexStatus` interface in `lib/mock-data.ts`: split into `reindex` and `retraining` sub-objects matching new API shape
- [ ] 5.2 Update `indexStatus` mock constant with split structure and realistic counter values
- [ ] 5.3 Add `RetrainingCounter` interface type for the counter sub-object

## 6. Frontend: Dashboard Split Cards

- [ ] 6.1 Split existing "Index Status" card in `Dashboard.tsx` into two cards: "Qdrant Index Health" and "Model Training Status"
- [ ] 6.2 "Qdrant Index Health" card: show status badge, items_updated/archived/feedback_accepted/contributions_accepted counts, "Re-index Qdrant" button with pre-flight dialog
- [ ] 6.3 "Model Training Status" card: show current model version, retraining counter breakdown, threshold progress bar, warning text when active, "Export YOLO Dataset" link, "Upload Candidate Model" link
- [ ] 6.4 Move retraining guidance dialog content to reference YOLO export instead of generic "Dataset Browser export"

## 7. Frontend: ModelIndex Page Update

- [ ] 7.1 Update `ModelIndex.tsx` to use split `indexStatus` types
- [ ] 7.2 Update "Retraining Guidance" dialog text to reference YOLO export from Dataset Browser
- [ ] 7.3 Ensure "Re-index Qdrant" button in ModelIndex matches Dashboard behavior

## 8. Frontend: Dataset Browser YOLO Export

- [ ] 8.1 Add "Export YOLO" button to `Dataset.tsx` filter bar (next to existing "Export CSV")
- [ ] 8.2 Wire YOLO export button to `GET /api/v1/dataset/export/yolo` with current active filters
- [ ] 8.3 Show estimated item count before triggering download
- [ ] 8.4 Handle loading state during export generation

## 9. Validation & Cleanup

- [ ] 9.1 Run `uv --directory backend run ruff check && uv --directory backend run ruff format --check`
- [ ] 9.2 Run `uv --directory backend run pytest` (ensure existing tests pass)
- [ ] 9.3 Run `pnpm --dir frontend lint && pnpm --dir frontend typecheck && pnpm --dir frontend build`
- [ ] 9.4 Verify no remaining references to `external_retraining_recommended` boolean in codebase
- [ ] 9.5 Verify CONTEXT.md matches implemented terms (already updated)
- [ ] 9.6 Manual browser check: Dashboard shows two cards, re-index button opens pre-flight, training card shows counter
- [ ] 9.7 Manual browser check: Dataset Browser has YOLO export button
