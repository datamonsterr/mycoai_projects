## Context

The product workflow spans backend image ingestion, segmentation, segment confirmation, feature extraction, and frontend review. The slow stages currently behave like synchronous black boxes: upload waits, segmentation can return a generic Internal Server Error, and the frontend mainly shows loading buttons instead of per-image or per-strain state.

Constraints:
- Backend product code MUST reimplement behavior locally and MUST NOT import directly from `research/`.
- Progress must be testable through API state, not only UI timing.
- Long-running image work needs bounded concurrency to avoid exhausting CPU, memory, or model resources.
- Frontend is React 19 + Vite and should use existing styling/test tooling.

## Goals / Non-Goals

**Goals:**
- Fix the current segmentation Internal Server Error with a failing regression test first.
- Expose per-image upload, segmentation, and feature extraction progress as completed/total counts plus status.
- Start segmentation immediately after each successful upload.
- Confirm segments per strain, then start feature extraction for that strain immediately.
- Make the frontend show visible progress and partially dim pending uploaded-file rows.
- Cover backend unit/API behavior, frontend state/rendering behavior, integration flow, e2e flow, and manual browser validation.

**Non-Goals:**
- Replacing the segmentation or feature extraction model.
- Adding a new queue service, websocket stack, or external dependency unless existing API polling is insufficient.
- Training or fine-tuning models.
- Changing the research experiment code.

## Decisions

1. Use backend-owned job state with polling-friendly responses.
   - Decision: represent batch workflow state in backend models/endpoints as per-image and per-strain records with status, error, completed count, total count, and percent.
   - Rationale: simplest contract for tests and UI; avoids adding websocket/SSE infrastructure before needed.
   - Alternative: streaming events. Rejected for now because polling is enough for visible progress and cheaper to test.

2. Use bounded concurrency for independent image work.
   - Decision: upload success schedules segmentation for that image through an existing in-process concurrency primitive or backend-local worker abstraction with a fixed limit.
   - Rationale: immediate feedback without unbounded CPU/model contention.
   - Alternative: process the full batch serially. Rejected because it preserves current wait behavior.

3. Keep segmentation failure isolated per image.
   - Decision: segmentation exceptions become per-image failed status with a user-readable error while the batch continues.
   - Rationale: one bad image must not block the whole batch.
   - Alternative: fail the whole batch. Rejected because batch UX needs partial progress.

4. Gate feature extraction by strain confirmation.
   - Decision: confirming all segments for one strain marks that strain confirmed and starts feature extraction for that strain only, then advances UI to the next strain.
   - Rationale: matches reviewer workflow and avoids all-or-nothing confirmation.
   - Alternative: keep one global confirm button. Rejected because it hides progress and delays feature extraction.

5. Reuse frontend state and API client patterns.
   - Decision: add the least state needed to render pending/uploaded/segmenting/confirmed/extracting/done/failed rows and `X/N` progress labels.
   - Rationale: avoids a new state-management dependency.
   - Alternative: introduce a job orchestration library. Rejected as unnecessary.

## Risks / Trade-offs

- In-process jobs can be lost on backend restart → keep statuses recoverable where existing persistence exists; otherwise surface failed/unknown state and keep design compatible with later durable queue.
- Polling can add request load → use one batch-level poll endpoint or reuse existing batch refresh cadence, not per-image polling.
- Concurrent model inference can exhaust resources → enforce a small default worker limit and test concurrency boundaries.
- Partial failures complicate UI → show failed rows inline and allow retry only if an existing retry path exists; otherwise keep retry out of scope.
- Feature extraction may start while user continues reviewing other strains → per-strain state must be independent.

## Migration Plan

1. Add regression coverage for the segmentation 500 and fix the backend failure path.
2. Add/extend backend batch progress contracts and bounded scheduling.
3. Update frontend upload and review screens to render progress from the contract.
4. Add integration/e2e/manual validation.
5. Rollback by disabling new per-image scheduling path and returning to existing synchronous batch behavior if needed.

## Open Questions

- Which existing endpoint currently owns batch upload orchestration and can safely become the batch progress source?
- Is backend job state already persisted in the database, or is current upload state memory/filesystem-backed?
- Should failed image rows block strain confirmation, or can users confirm only successfully segmented images?
