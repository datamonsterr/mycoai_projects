# Bug 002: No download template button in Index New Data or Retrieve view

**Status:** CONFIRMED | **Severity:** Medium | **Component:** Frontend + Backend

## Root Cause

Feature not implemented. No template CSV, no backend endpoint, no AGENTS.md reference exists anywhere in the codebase.

**Evidence:**
- `IndexNewData.tsx:159` — only "Load Sample Data" button
- `Retrieve.tsx:702-703` — only "Load Single Sample" and "Load Batch Sample" buttons
- Backend: zero results for "template" / "csv_template" / "download.*csv" across all `.py` files
- No CSV template in `frontend/public/`

## Expected Flow

1. User clicks "Download Template" → gets CSV with AGENTS.md instructions
2. Template defines columns: `strain_name,species_name,media_name,image_path`
3. User fills template with their data
4. User uploads filled template
5. System validates structure and starts batch segmentation + identification
6. Results shown as multiple prediction visualizations

## Solution

**Frontend:** Add "Download Template" button in both `IndexNewData.tsx` and `Retrieve.tsx`. Generate CSV blob client-side or fetch from backend.

**Backend (optional):** Add `GET /api/v1/templates/upload` returning `text/csv`.

**AGENTS.md:** Include in template package with instructions on expected database structure.

## Files to Modify

- `frontend/src/pages/IndexNewData.tsx` (~line 158-160)
- `frontend/src/pages/Retrieve.tsx` (~line 700-704)
- `frontend/src/lib/template.ts` (new file — template CSV generator)
