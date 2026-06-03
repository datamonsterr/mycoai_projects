from fastapi import APIRouter, Depends, Query

from ..core.dependencies import get_current_user, require_role
from ..core.pagination import PageParams, PaginatedResponse
from ..schemas import SpeciesCreateRequest, SpeciesItem, SpeciesUpdateRequest
from ..services.stores import as_paginated, get_species_store, new_id, utcnow

router = APIRouter()


@router.get("", response_model=PaginatedResponse[SpeciesItem])
def list_species(
    params: PageParams = Depends(),
    user: dict = Depends(get_current_user),
    search: str | None = Query(None),
    sort_by: str | None = Query(None),
    sort_order: str | None = Query(None),
) -> dict:
    store = get_species_store()
    items = [s for s in store.list() if not s.get("is_archived", False)]
    if search:
        items = [s for s in items if search.lower() in s.get("name", "").lower()]
    items_with_count = [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s.get("description"),
            "is_archived": s.get("is_archived", False),
            "count": 0,
        }
        for s in items
    ]
    page_items, total = as_paginated(items_with_count, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.post("", response_model=SpeciesItem, status_code=201)
def create_species(
    data: SpeciesCreateRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    store = get_species_store()
    item_id = new_id()
    item = {
        "id": item_id,
        "name": data.name,
        "description": data.description,
        "is_archived": False,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    store.put(item)
    return {
        "id": item_id,
        "name": data.name,
        "description": data.description,
        "is_archived": False,
        "count": 0,
    }


@router.get("/{species_id}", response_model=SpeciesItem)
def get_species(species_id: str, user: dict = Depends(get_current_user)) -> dict:
    from ..core.exceptions import NotFoundError

    s = get_species_store().get(species_id)
    if not s:
        raise NotFoundError(f"Species {species_id} not found")
    return {
        "id": s["id"],
        "name": s["name"],
        "description": s.get("description"),
        "is_archived": s.get("is_archived", False),
        "count": 0,
    }


@router.patch("/{species_id}", response_model=SpeciesItem)
def update_species(
    species_id: str,
    data: SpeciesUpdateRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_species_store()
    s = store.get(species_id)
    if not s:
        raise NotFoundError(f"Species {species_id} not found")
    if data.name is not None:
        s["name"] = data.name
    if data.description is not None:
        s["description"] = data.description
    s["updated_at"] = utcnow()
    store.put(s)
    return {
        "id": s["id"],
        "name": s["name"],
        "description": s.get("description"),
        "is_archived": s.get("is_archived", False),
        "count": 0,
    }


@router.delete("/{species_id}", status_code=204)
def delete_species(
    species_id: str,
    user: dict = Depends(require_role("owner")),
) -> None:
    from ..core.exceptions import NotFoundError

    store = get_species_store()
    s = store.get(species_id)
    if not s:
        raise NotFoundError(f"Species {species_id} not found")
    s["is_archived"] = True
    store.put(s)
