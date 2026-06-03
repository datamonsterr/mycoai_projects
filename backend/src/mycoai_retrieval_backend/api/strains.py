from fastapi import APIRouter, Depends, Query

from ..core.dependencies import get_current_user, require_role
from ..core.pagination import PageParams, PaginatedResponse
from ..schemas import StrainCreateRequest, StrainItem
from ..services.stores import as_paginated, get_strain_store, new_id, utcnow

router = APIRouter()


@router.get("", response_model=PaginatedResponse[StrainItem])
def list_strains(
    params: PageParams = Depends(),
    user: dict = Depends(get_current_user),
    species_id: str | None = Query(None),
    media: str | None = Query(None),
    is_archived: bool | None = Query(None),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
) -> dict:
    store = get_strain_store()
    items = list(store.list())
    if species_id:
        items = [s for s in items if s.get("species_id") == species_id]
    if is_archived is not None:
        items = [s for s in items if s.get("is_archived", False) == is_archived]
    if search:
        items = [s for s in items if search.lower() in s.get("name", "").lower()]
    result = [
        {
            "id": s["id"],
            "name": s["name"],
            "species_id": s["species_id"],
            "source": s.get("source", "user_upload"),
            "is_archived": s.get("is_archived", False),
            "images": s.get("images", []),
        }
        for s in items
    ]
    page_items, total = as_paginated(result, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.post("", response_model=StrainItem, status_code=201)
def create_strain(
    data: StrainCreateRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    strain_id = new_id()
    item = {
        "id": strain_id,
        "name": data.name,
        "species_id": data.species_id,
        "source": data.source,
        "is_archived": False,
        "images": data.images,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    get_strain_store().put(item)
    return {
        "id": strain_id,
        "name": data.name,
        "species_id": data.species_id,
        "source": data.source,
        "is_archived": False,
        "images": data.images,
    }


@router.get("/{strain_id}", response_model=StrainItem)
def get_strain(strain_id: str, user: dict = Depends(get_current_user)) -> dict:
    from ..core.exceptions import NotFoundError

    s = get_strain_store().get(strain_id)
    if not s:
        raise NotFoundError(f"Strain {strain_id} not found")
    return {
        "id": s["id"],
        "name": s["name"],
        "species_id": s["species_id"],
        "source": s.get("source", "user_upload"),
        "is_archived": s.get("is_archived", False),
        "images": s.get("images", []),
    }


@router.delete("/{strain_id}", status_code=204)
def delete_strain(
    strain_id: str,
    user: dict = Depends(require_role("owner")),
) -> None:
    from ..core.exceptions import NotFoundError

    store = get_strain_store()
    s = store.get(strain_id)
    if not s:
        raise NotFoundError(f"Strain {strain_id} not found")
    s["is_archived"] = True
    store.put(s)
