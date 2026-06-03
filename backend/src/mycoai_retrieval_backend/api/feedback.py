from fastapi import APIRouter, Depends

from ..core.dependencies import get_current_user, require_role
from ..core.pagination import PageParams, PaginatedResponse
from ..schemas import (
    FeedbackBatchRequest,
    FeedbackCreateRequest,
    FeedbackItem,
    FeedbackUpdateRequest,
)
from ..services.stores import as_paginated, get_feedback_store, new_id, utcnow

router = APIRouter()


@router.post("", response_model=FeedbackItem, status_code=201)
def submit_feedback(
    data: FeedbackCreateRequest,
    user: dict = Depends(get_current_user),
) -> dict:
    item_id = new_id()
    item = {
        "id": item_id,
        "submitter_id": user["id"],
        "reviewer_id": None,
        "source": data.source,
        "query_strain": data.query_strain,
        "result_id": data.result_id,
        "image_id": data.image_id,
        "predicted_species": data.predicted_species,
        "suggested_species": data.suggested_species,
        "description": data.description,
        "status": "pending",
        "review_note": None,
        "submitted_at": utcnow(),
        "reviewed_at": None,
    }
    get_feedback_store().put(item)
    return {
        "id": item_id,
        "submitter_id": item["submitter_id"],
        "reviewer_id": None,
        "source": item["source"],
        "status": "pending",
        "suggested_species": item["suggested_species"],
        "description": item["description"],
    }


@router.get("", response_model=PaginatedResponse[FeedbackItem])
def list_my_feedback(
    params: PageParams = Depends(),
    user: dict = Depends(get_current_user),
) -> dict:
    store = get_feedback_store()
    items = [f for f in store.list() if f["submitter_id"] == user["id"]]
    result = [
        {
            "id": f["id"],
            "submitter_id": f["submitter_id"],
            "reviewer_id": f.get("reviewer_id"),
            "source": f["source"],
            "status": f["status"],
            "suggested_species": f.get("suggested_species", ""),
            "description": f.get("description", ""),
        }
        for f in items
    ]
    page_items, total = as_paginated(result, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.get("/inbox", response_model=PaginatedResponse[FeedbackItem])
def feedback_inbox(
    params: PageParams = Depends(),
    user: dict = Depends(require_role("owner")),
) -> dict:
    store = get_feedback_store()
    items = [f for f in store.list() if f["status"] == "pending"]
    result = [
        {
            "id": f["id"],
            "submitter_id": f["submitter_id"],
            "reviewer_id": f.get("reviewer_id"),
            "source": f["source"],
            "status": f["status"],
            "suggested_species": f.get("suggested_species", ""),
            "description": f.get("description", ""),
        }
        for f in items
    ]
    page_items, total = as_paginated(result, params.offset, params.limit)
    return {
        "items": page_items,
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.patch("/{feedback_id}", response_model=FeedbackItem)
def update_feedback(
    feedback_id: str,
    data: FeedbackUpdateRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_feedback_store()
    f = store.get(feedback_id)
    if not f:
        raise NotFoundError(f"Feedback {feedback_id} not found")
    f["status"] = data.status
    f["reviewer_id"] = user["id"]
    if data.review_note is not None:
        f["review_note"] = data.review_note
    f["reviewed_at"] = utcnow()
    store.put(f)
    return {
        "id": f["id"],
        "submitter_id": f["submitter_id"],
        "reviewer_id": f.get("reviewer_id"),
        "source": f["source"],
        "status": f["status"],
        "suggested_species": f.get("suggested_species", ""),
        "description": f.get("description", ""),
    }


@router.post("/batch", status_code=200)
def batch_feedback(
    data: FeedbackBatchRequest,
    user: dict = Depends(require_role("owner")),
) -> dict:
    store = get_feedback_store()
    updated = 0
    for fid in data.ids:
        f = store.get(fid)
        if f:
            f["status"] = data.status
            f["reviewer_id"] = user["id"]
            f["reviewed_at"] = utcnow()
            store.put(f)
            updated += 1
    return {"updated": updated}
