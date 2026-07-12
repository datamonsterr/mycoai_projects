# Dataset Browser strain-group rows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Dataset Browser from image rows to strain-group rows with expandable child image rows, removing the `Plate` column, image ID text, and segment count from the UI.

**Architecture:** Add or refactor a dataset-browser API to return strain-group rows with child image items filtered at query time. Update the Dataset page and image service types to consume the grouped contract. Keep image mutations scoped to child rows. Add regression tests before the implementation change so the new grouped UX is pinned.

**Tech Stack:** React 19 + Vite + TanStack Query + Vitest/Testing Library, FastAPI + SQLAlchemy + Pydantic + pytest, pnpm, uv.

---

## File map

- Modify: `frontend/src/pages/Dataset.tsx`
- Modify: `frontend/src/services/images.ts`
- Modify: `frontend/src/services/types.ts`
- Modify: `frontend/src/hooks/use-images.ts`
- Modify: `frontend/src/__tests__/dataset-page.test.tsx` if present, else add a focused dataset page test file
- Modify: `backend/src/backend/routes.py`
- Modify: `backend/src/backend/schemas/__init__.py`
- Modify: `backend/tests/` dataset browser API tests if present, else add focused ones
- Optional modify: `CONTEXT.md` only if implementation uncovers new canonical wording that is not already captured

### Task 1: Reproduce current dataset-browser mismatch in frontend tests

**Files:**
- Modify: `frontend/src/__tests__/dataset-page.test.tsx` or add a focused dataset browser test file
- Read for reference: `frontend/src/pages/Dataset.tsx`

- [ ] Add failing tests that describe the target UX: one top-level row per strain, no `Plate` header, no visible image ID, no visible segment count, expand reveals child image rows with preview/created/status/qdrant/actions.
- [ ] Mock grouped API data with one strain containing at least two images so expansion behavior is explicit.
- [ ] Run: `pnpm --dir frontend test -- dataset`
- [ ] Confirm the failures come from the current flat image-row implementation, not bad mocks.

### Task 2: Reproduce grouped dataset-browser contract in backend tests

**Files:**
- Modify: focused backend dataset browser tests under `backend/tests/`
- Read for reference: `backend/src/backend/routes.py`
- Read for reference: `backend/src/backend/schemas/__init__.py`

- [ ] Add failing API tests for grouped strain results.
- [ ] Cover: total counts strain groups, search by strain name, media/species/status filters, child image rows omit segment-count dependency, and matching groups only include matching child images.
- [ ] Run focused backend tests for the dataset browser endpoint.
- [ ] Confirm the current flat `ImageListResponse` fails these grouped assertions.

### Task 3: Define grouped response schemas

**Files:**
- Modify: `backend/src/backend/schemas/__init__.py`
- Modify: `frontend/src/services/types.ts`
- Modify: `frontend/src/services/images.ts`

- [ ] Introduce backend schemas for strain-group rows and child image items.
- [ ] Keep child payload minimal: image id, source_url, created_at, data_update_status, indexed_in_qdrant, is_archived, and any field still needed by child-row actions.
- [ ] Mirror those types in frontend service types.
- [ ] Decide whether to keep `listImages` naming or rename to a dataset-browser-specific name; prefer the smallest safe diff.

### Task 4: Implement grouped backend query

**Files:**
- Modify: `backend/src/backend/routes.py`
- Read for reference: `backend/src/backend/models/__init__.py`

- [ ] Refactor the dataset-browser list handler to build strain groups instead of flat image rows, or add a new grouped route if the flat response is reused elsewhere.
- [ ] Keep search/filter predicates on image/strain joins, then group the matching images by strain.
- [ ] Ensure `total` counts returned strain groups, not images.
- [ ] Build parent media summary from distinct child image media names.
- [ ] Preserve child image `source_url`, archive state, and qdrant-indexed derivation.
- [ ] Run focused backend tests until green.

### Task 5: Refactor Dataset page to strain-parent rows

**Files:**
- Modify: `frontend/src/pages/Dataset.tsx`
- Modify: `frontend/src/hooks/use-images.ts`
- Modify: `frontend/src/services/images.ts`
- Modify: `frontend/src/services/types.ts`

- [ ] Replace flat `images` rendering with parent `strainGroups` rendering.
- [ ] Parent columns: expand chevron, strain, species, media, images count.
- [ ] Remove the `Plate` thumbnail column.
- [ ] Change expanded content from a freeform image detail card to child image rows or a nested table.
- [ ] Child rows show preview, created date, status badge, qdrant badge, and owner-only actions.
- [ ] Do not render visible image ID or segment count anywhere in the dataset browser.
- [ ] Update empty/loading labels to match strain semantics.
- [ ] Re-run the focused frontend dataset tests.

### Task 6: Tighten UI behavior + edge cases

**Files:**
- Modify: `frontend/src/pages/Dataset.tsx`
- Modify: `frontend/src/__tests__/dataset-page.test.tsx` or focused dataset test file

- [ ] Verify expansion state keys use `strain_id`, not child image id.
- [ ] Ensure archived child images still render with reduced emphasis if that was the prior visual rule.
- [ ] Handle multiple child media values in the parent row with a compact readable label.
- [ ] Keep owner/dataowner action visibility correct on child rows only.
- [ ] Re-run all dataset page tests.

### Task 7: Frontend verification sweep

**Files:**
- Any touched frontend files above

- [ ] Run: `pnpm --dir frontend test`
- [ ] Run: `pnpm --dir frontend lint`
- [ ] Run: `pnpm --dir frontend typecheck`
- [ ] Run: `pnpm --dir frontend build`
- [ ] If a check fails because of pre-existing issues, record the exact failure and whether this change caused it.

### Task 8: Backend verification sweep

**Files:**
- Any touched backend files above

- [ ] Run: `uv --directory backend run pytest`
- [ ] Run: `uv --directory backend run ruff check .`
- [ ] Run: `uv --directory backend run mypy src`
- [ ] If endpoint naming or contract changed, rerun any higher-level API tests touching dataset browsing.

### Task 9: Manual validation

**Files:**
- None, unless small fixes are needed

- [ ] Start backend + frontend locally.
- [ ] Verify Dataset Browser now shows one parent row per strain.
- [ ] Expand a strain with multiple images and confirm child rows show preview, created, status, qdrant, and actions only.
- [ ] Confirm `Plate`, visible image ID, and segment count are absent.
- [ ] Confirm search/filter results stay coherent when only some child images match.

### Task 10: Final handoff

**Files:**
- Any touched files above

- [ ] Summarize whether the endpoint was changed in place or split into a new grouped route.
- [ ] Record test commands and outcomes.
- [ ] Record any remaining risk, especially if another screen still depends on the old flat image-list contract.
