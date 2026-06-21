# Bug 005: 403 Forbidden on /api/v1/admin/users for data-owner role

**Status:** CONFIRMED | **Severity:** High | **Component:** Backend

## Root Cause

`backend/src/core/dependencies.py:57` — `require_owner()` checks only `user.role != "owner"`, rejecting `"dataowner"` role entirely.

```python
if user.role != "owner":
    raise AuthorizationError("Role 'owner' required")
```

User `phamdat17092004@gmail.com` has `role = "dataowner"` but the endpoint requires `"owner"`. All `/admin/users` endpoints use `CurrentOwner` dependency.

**Frontend inconsistency:** `App.tsx:29` correctly treats `dataowner === owner` for routing, `layout.tsx:37-46` shows admin nav items with `roles: ['owner', 'dataowner']`, but `Dashboard.tsx:124` and `ModelIndex.tsx:21` use only `user?.role === 'owner'`.

## Solution

1. **Backend:** Change `require_owner()` to accept both `"owner"` and `"dataowner"`:
   ```python
   if user.role not in ("owner", "dataowner"):
   ```
   Or create `require_admin()` that both dependencies use.

2. **Backend:** `admin.py:105,142` — protect both owner and dataowner from demotion:
   ```python
   if target.role in ("owner", "dataowner") and data.role == "user":
   ```

3. **Backend:** `repos/user.py:53` — count both roles in `count_active_owners`:
   ```python
   .where(User.role.in_(["owner", "dataowner"]), User.is_active.is_(True))
   ```

4. **Frontend:** `Dashboard.tsx:124`, `ModelIndex.tsx:21`:
   ```ts
   const isOwner = user?.role === 'owner' || user?.role === 'dataowner'
   ```

## Files to Modify

- `backend/src/core/dependencies.py` (lines 44, 57)
- `backend/src/api/admin.py` (lines 105, 142)
- `backend/src/repos/user.py` (line 53)
- `frontend/src/pages/Dashboard.tsx` (line 124)
- `frontend/src/pages/ModelIndex.tsx` (line 21)
