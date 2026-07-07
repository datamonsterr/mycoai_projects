## Why

Batch upload, segmentation, and feature extraction are long-running image workflows. Today failures surface as generic 500 errors and the frontend hides work behind indefinite loading states, leaving users unable to see per-image or per-strain progress.

## What Changes

- Debug and fix the backend segmentation Internal Server Error path, with tests that reproduce the failure.
- Add progress-aware batch upload behavior that reports uploaded images out of total images and appends successful uploads immediately.
- Start segmentation as soon as each image uploads successfully, using bounded concurrent processing instead of waiting for the entire batch.
- Change the frontend batch UI so pending files render at 50% opacity and successful uploads render fully visible.
- Replace all-or-nothing segment confirmation with per-strain confirmation; after all segments in a strain are confirmed, feature extraction starts for that strain immediately.
- Advance to the next strain tab after confirming a strain and show progress as `X/N` strains in the confirmation button.
- Show job progress for upload, segmentation, and feature extraction as `X/N` images and percentage where applicable.
- Update backend, frontend, integration, e2e, and manual browser validation coverage for the new workflow.

## Capabilities

### New Capabilities
- `batch-processing-progress`: Progress-aware batch upload, per-image segmentation, per-strain confirmation, and per-strain feature extraction workflow.

### Modified Capabilities

## Impact

- Backend: segmentation pipeline, batch upload endpoints, background/concurrent processing, progress status models, API tests.
- Frontend: batch upload UI, segmentation review UI, strain tabs, progress indicators, disabled/loading states, e2e tests.
- Contracts: API responses/events must expose per-image and per-strain status without importing research runtime code.
- Validation: backend ruff/format/mypy/pytest; frontend lint/typecheck/build/e2e; manual browser test with agent-browser skill.
