# Bug 009: Dashboard — missing charts, index status row, card alignment

**Status:** CONFIRMED | **Severity:** Medium | **Component:** Frontend + Backend

## Root Cause

Four distinct issues in `frontend/src/pages/Dashboard.tsx` and backend.

### 1. Missing charts from dataset_eda.py

Dashboard shows only species/media pie charts + 4 aggregate counts. Missing:
- Strain distribution chart
- Environment distribution chart
- Collection-level stats (quality tiers, parse status, etc.)
- `total_environments` metric

**Backend gap:** `schemas/dashboard.py` has no `total_environments`, no strain/environment distribution endpoints.

### 2. Index Status in wrong row (`Dashboard.tsx:191-269`)

Index Status card is in a `lg:grid-cols-3` row with two tall pie charts. Should be in its own dedicated row for visual hierarchy.

### 3. Card border/height issues (`Dashboard.tsx:177`)

Metrics grid on line 177 has no `auto-rows-fr` — cards size to content, causing misalignment:
```tsx
<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
```

### 4. Card alignment (`Dashboard.tsx:179`)

Each Card uses `flex items-stretch` but parent grid doesn't enforce equal heights.

## Solution

**Backend:**
- Add `total_environments: int` to `DashboardStats` (`schemas/dashboard.py:4-9`)
- Add `/dashboard/charts/strain-distribution` and `/dashboard/charts/environment-distribution` endpoints (`api/dashboard.py` after line 79)

**Frontend:**
- Add `useStrainDistribution`, `useEnvironmentDistribution` hooks (`hooks/use-dashboard.ts`)
- Add new PieChart components for strain and environment distributions
- Move Index Status to its own row before chart row
- Change chart grid from `lg:grid-cols-3` to `lg:grid-cols-2`
- Add `auto-rows-fr` to metrics grid, `h-full` to each metrics Card

## Files to Modify

- `backend/src/mycoai_retrieval_backend/schemas/dashboard.py` (lines 4-9)
- `backend/src/mycoai_retrieval_backend/api/dashboard.py` (after line 79)
- `frontend/src/services/types.ts` (lines 216-221)
- `frontend/src/hooks/use-dashboard.ts` (lines 7-11, after 29)
- `frontend/src/services/dashboard.ts` (lines 12-17)
- `frontend/src/pages/Dashboard.tsx` (lines 7-11, 124, 128, 166, 177, 179, 191-269)
