# Retrieve tabs + async upload + retrieval sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor Retrieve Species into single-strain and batch tabs, keep single-image uploads async/segmentation-only, fix backend retrieval/RBAC/API issues, and sync product SQL/Qdrant/MinIO data with research fold0 vectors.

**Architecture:** Reuse the proven `IndexNewData` tab/upload interaction in `frontend/src/pages/Retrieve.tsx` instead of inventing a new flow. Add focused regression tests first, then fix backend API/RBAC defects blocking retrieve flows, then run a one-off sync path that copies validated vector+metadata state into product services.

**Tech Stack:** React 19 + Vite + Vitest + Testing Library, FastAPI + SQLAlchemy + Alembic, Qdrant, MinIO, uv, pnpm.

---

## File map

- Modify: `frontend/src/pages/Retrieve.tsx`
- Modify: `frontend/src/__tests__/retrieve-page.test.tsx`
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/api/models.py`
- Modify: `backend/src/backend/api/training.py`
- Modify: `backend/src/backend/routes.py`
- Modify: `backend/scripts/sync_qdrant_to_sql.py`
- Add: `backend/scripts/sync_research_fold0_to_product.py`
- Modify: `backend/tests/` existing retrieval/RBAC test files if present, else add focused ones

### Task 1: Reproduce retrieve upload UX bugs

**Files:**
- Modify: `frontend/src/__tests__/retrieve-page.test.tsx`
- Modify: `frontend/src/pages/Retrieve.tsx`

- [ ] Add failing tests for: tab labels mirroring index page, batch tab owner/dataowner only, single upload keeps add-image CTA visible while upload pending, single upload does not auto-advance to retrieval/results.
- [ ] Run: `pnpm --dir frontend test -- retrieve-page.test.tsx`
- [ ] Confirm failures map to current behavior, not broken mocks.

### Task 2: Minimal retrieve UI refactor

**Files:**
- Modify: `frontend/src/pages/Retrieve.tsx`

- [ ] Reuse `TabsList/TabsTrigger` layout from `IndexNewData.tsx` for `Single strain` / `Batch processing` in upload step.
- [ ] Move ZIP card inside batch tab; keep hidden for non-owner roles.
- [ ] Keep `Add image` button rendered during async upload; track per-image pending state instead of blocking entire card.
- [ ] Change single-upload handler to upload + segment only; do not jump to `results` or trigger reindex/retrieval automatically.
- [ ] Keep explicit next actions: `Segment All`, `Extract All`, `Run Retrieval`.
- [ ] Run: `pnpm --dir frontend test -- retrieve-page.test.tsx`

### Task 3: Frontend regression sweep

**Files:**
- Modify: `frontend/src/__tests__/retrieve-page.test.tsx`
- Modify: `frontend/src/pages/Retrieve.tsx`

- [ ] Tighten assertions for batch progress rows, owner/dataowner visibility, and no duplicate CTA disappearance during async uploads.
- [ ] Run: `pnpm --dir frontend test`
- [ ] Run: `pnpm --dir frontend lint`
- [ ] Run: `pnpm --dir frontend typecheck`
- [ ] Run: `pnpm --dir frontend build`

### Task 4: Reproduce backend retrieve/RBAC/API bugs

**Files:**
- Modify: `backend/tests/...` focused retrieval/auth tests
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/api/models.py`
- Modify: `backend/src/backend/api/training.py`
- Modify: `backend/src/backend/routes.py`

- [ ] Add or extend tests for dataowner access parity, retrieval error responses, safe evidence/file handling, and image segment URL behavior under MinIO/S3.
- [ ] Run focused backend tests to reproduce failures.

### Task 5: Backend bugfixes

**Files:**
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/api/models.py`
- Modify: `backend/src/backend/api/training.py`
- Modify: `backend/src/backend/routes.py`

- [ ] Replace strict owner-only guards with owner+dataowner where intended for product flows.
- [ ] Stop swallowing retrieval failures that should return structured API errors.
- [ ] Fix segment/source URL handling so MinIO-backed segments resolve correctly.
- [ ] Re-run focused backend tests, then broader checks:
  - `uv --directory backend run ruff check .`
  - `uv --directory backend run mypy src`
  - `uv --directory backend run pytest`

### Task 6: Product data sync from research fold0

**Files:**
- Modify: `backend/scripts/sync_qdrant_to_sql.py`
- Add: `backend/scripts/sync_research_fold0_to_product.py`

- [ ] Inspect current product SQL image count vs research fold0 Qdrant count.
- [ ] Implement one-off sync script that reads research collection `qdrant-research_fold0` vector `efficientnetb1_finetuned`, writes/updates product SQL metadata, and verifies segment objects exist in MinIO.
- [ ] Keep script idempotent: update missing rows, skip already-synced rows, report mismatches.
- [ ] Run script in dry-run/scan mode first, then real sync.

### Task 7: Manual browser/API validation

**Files:**
- None or small fixes from validation

- [ ] Start backend + frontend locally.
- [ ] Use agent-browser/manual-browser path to verify:
  - user retrieve flow
  - dataowner retrieve flow
  - single async upload keeps add-image visible
  - batch tab works
  - API errors surface sanely
- [ ] If defects found, add focused regression tests, fix, rerun checks.

### Task 8: Final verification

**Files:**
- Any touched above

- [ ] Frontend: `pnpm --dir frontend lint && pnpm --dir frontend typecheck && pnpm --dir frontend build && pnpm --dir frontend test`
- [ ] Backend: `uv --directory backend run ruff check . && uv --directory backend run mypy src && uv --directory backend run pytest`
- [ ] Record sync counts and manual validation notes in final handoff.
