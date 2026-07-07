## 1. Backend Failure Reproduction

- [x] 1.1 Identify the current batch upload, segmentation, segment confirmation, and feature extraction endpoints and data models.
- [x] 1.2 Add a backend regression test that reproduces the current segmentation Internal Server Error path.
- [x] 1.3 Fix segmentation error handling so known invalid image/model/artifact states become per-image failed status or non-500 API errors.
- [x] 1.4 Add tests proving one segmentation failure does not stop other images in the same batch.

## 2. Backend Progress Contract

- [x] 2.1 Add or extend backend response models for per-image status, per-strain status, completed count, total count, percent, and safe error text.
- [x] 2.2 Add or extend a batch progress endpoint so the frontend can poll one batch-level progress source.
- [x] 2.3 Update upload handling so each successful file upload immediately records uploaded status and count.
- [x] 2.4 Add backend tests for upload progress counts and immediate uploaded-list updates.

## 3. Concurrent Image Processing

- [x] 3.1 Add bounded backend scheduling for segmentation after each successful image upload.
- [x] 3.2 Ensure segmentation concurrency has a configurable or constant limit and never runs unbounded.
- [x] 3.3 Add integration tests proving segmentation starts before the full batch upload completes.
- [x] 3.4 Add tests proving the configured segmentation concurrency limit is respected.

## 4. Per-Strain Confirmation and Extraction

- [x] 4.1 Update segment confirmation API behavior to confirm one strain independently.
- [x] 4.2 Start feature extraction immediately after all segments in one strain are confirmed.
- [x] 4.3 Add per-strain feature extraction progress counts and percentage to backend progress state.
- [x] 4.4 Add backend/API tests for per-strain confirmation, automatic feature extraction start, and per-strain progress.

## 5. Frontend Progress UX

- [x] 5.1 Locate the current frontend batch upload and segmentation review components and API client calls.
- [x] 5.2 Render upload progress as uploaded files over total files and percentage.
- [x] 5.3 Append each successfully uploaded file to the uploaded list immediately.
- [x] 5.4 Render pending upload rows at 50% opacity and successful uploaded rows at full opacity.
- [x] 5.5 Render segmentation and feature extraction progress as `X/N` images and percentage.
- [x] 5.6 Replace global segment confirmation with active-strain confirmation.
- [x] 5.7 Show confirmed strains as `X/N` in the confirmation control.
- [x] 5.8 Advance to the next strain tab after confirming the active strain.
- [x] 5.9 Render per-image/per-strain failed states inline without infinite loading buttons.

## 6. Frontend and E2E Tests

- [x] 6.1 Add frontend tests for upload progress rendering and 50% opacity on pending files.
- [x] 6.2 Add frontend tests for immediate uploaded-list append behavior.
- [x] 6.3 Add frontend tests for per-strain confirmation progress and next-tab advancement.
- [x] 6.4 Add frontend tests for segmentation and feature extraction progress labels.
- [x] 6.5 Add or update Playwright e2e coverage for multi-file upload, segmentation progress, per-strain confirmation, and feature extraction progress.

## 7. Validation

- [x] 7.1 Run backend validation: `uv --directory backend run ruff check .`, `uv --directory backend run ruff format --check .`, `uv --directory backend run mypy .`, and `uv --directory backend run pytest`.
- [x] 7.2 Run frontend validation: `pnpm --dir frontend lint`, `pnpm --dir frontend typecheck`, and `pnpm --dir frontend build`.
- [x] 7.3 Run frontend e2e tests with the repo Playwright command.
- [x] 7.4 Perform and record an agent-browser manual test for the batch upload through feature extraction workflow.
- [x] 7.5 Update implementation summary with validation evidence, contract impacts, and residual risks.
