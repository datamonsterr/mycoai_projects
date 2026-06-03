from fastapi import APIRouter, Depends

from ..core.dependencies import require_role
from ..core.pagination import PageParams, PaginatedResponse
from ..schemas import AdminRoleUpdateRequest, AdminUserItem
from ..services.stores import (
    as_paginated,
    get_admin_audit_store,
    get_user_store,
    utcnow,
)

router = APIRouter()


@router.get("/users", response_model=PaginatedResponse[AdminUserItem])
def list_users(
    params: PageParams = Depends(),
    user: dict = Depends(require_role("owner")),
) -> dict:
    store = get_user_store()
    items = [
        {
            "id": u["id"],
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "is_active": u.get("is_active", True),
        }
        for u in store.list()
    ]
    page_items, total = as_paginated(items, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.patch("/users/{user_id}/role", response_model=AdminUserItem)
def update_user_role(
    user_id: str,
    data: AdminRoleUpdateRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_user_store()
    target = store.get(user_id)
    if not target:
        raise NotFoundError(f"User {user_id} not found")
    target["role"] = data.role
    store.put(target)
    audit = {"id": user_id, "action": "role_change", "role": data.role, "at": utcnow()}
    get_admin_audit_store().put(audit)
    return {
        "id": target["id"],
        "email": target["email"],
        "name": target["name"],
        "role": target["role"],
        "is_active": target.get("is_active", True),
    }


@router.get("/audit-log")
def audit_log(
    params: PageParams = Depends(),
    user: dict = Depends(require_role("owner")),
) -> dict:
    store = get_admin_audit_store()
    items = list(store.list())
    page_items, total = as_paginated(items, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }
