# Bug 003: Remove all test metadata/strain from database

**Status:** CONFIRMED (gap exists) | **Severity:** Low | **Component:** Backend

## Root Cause

No bulk test-data cleanup endpoint. Three types of "test data" exist:

**A) In-memory seed data** (`backend/.../services/stores.py:49-105`)
- Test users, species, strains created in `MemoryStore`
- Ephemeral — process restart clears them
- Only active when Postgres is NOT configured

**B) Frontend sample assets** (`frontend/src/lib/sample-assets.ts`)
- Static JSON for demo strains (T379 thymicola, T362 sclerotigenum)
- Not stored in any database, only used by "Load Sample" buttons

**C) Real DB data** (Postgres)
- No `DELETE /admin/cleanup-test-data` endpoint exists

## Solution

Add an owner-only cleanup endpoint:

```python
@router.delete("/admin/test-data", tags=["Admin"])
async def clear_test_data(
    strain_pattern: str = "T%",
    db=Depends(get_db),
    user=Depends(require_admin()),
):
    """Delete test strains and their images matching the given pattern."""
```

Cascade: images → segments → Qdrant entries → strains → orphan species.

## Files to Modify

- `backend/src/mycoai_retrieval_backend/api/admin.py` — new cleanup endpoint
