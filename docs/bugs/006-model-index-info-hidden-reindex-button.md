# Bug 006: Model & Index info not displayed, no reindex button for data-owner

**Status:** CONFIRMED | **Severity:** High | **Component:** Backend + Frontend

## Root Cause

Two-tier issue — same role gate as Bug 005 plus frontend `isOwner` checks.

**Backend:** All `/training/*` and `/index/*` endpoints gate on `require_role("owner")` or `CurrentOwner`, both rejecting `"dataowner"`. See `training.py:34,54,69,92,104` and `index.py:28,216`.

**Frontend:** `Dashboard.tsx:124` uses `user?.role === 'owner'` — dataowner excluded from "Re-index Qdrant" button (line 228). `ModelIndex.tsx:21` same issue — dataowner excluded from all training/index action buttons.

**Dashboard Qdrant endpoint:** `dashboard.py:92-96` returns hardcoded `{"learned": 0, "unlearned": 0}` — no actual Qdrant query.

The API response includes correct fields (`reindex`, `retraining`, `current_model_version`) but the frontend doesn't display them because of the role check + the model page may not be rendering the data properly.

## Solution

1. Fix backend role gates per Bug 005
2. Fix frontend `isOwner` checks per Bug 005
3. Wire `dashboard.py:qdrant_status` to query real Qdrant collection stats
4. Verify Qdrant Docker data matches `Dataset/` contents

## Qdrant Verification

Check Docker Qdrant data:
```bash
# Check if Qdrant container is running
docker ps | grep qdrant
# Query collection stats
curl http://localhost:6333/collections/myco_fungi_features_full
```

Re-run retrieval experiment to verify:
```bash
uv --directory research run python src/experiments/retrieval/run.py
```

## Files to Modify

- Same as Bug 005, plus:
- `backend/src/mycoai_retrieval_backend/api/training.py` (lines 34, 54, 69, 92, 104)
- `backend/src/mycoai_retrieval_backend/api/index.py` (lines 28, 216)
- `backend/src/mycoai_retrieval_backend/api/dashboard.py` (lines 92-96)
