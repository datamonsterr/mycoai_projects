from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_owner
from ..core.exceptions import NotFoundError
from ..core.pagination import PageParams, PaginatedResponse
from ..database import get_db
from ..models import Feedback, User
from ..repos.feedback import FeedbackRepository
from ..schemas.feedback import (
    FeedbackBatchRequest,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)

router = APIRouter()


def _feedback_to_response(f: Feedback) -> FeedbackResponse:
    return FeedbackResponse(
        id=str(f.id),
        submitter_id=str(f.submitter_id),
        reviewer_id=str(f.reviewer_id) if f.reviewer_id else None,
        source=f.source,
        feedback_type=f.feedback_type,
        query_strain=f.query_strain,
        result_id=str(f.result_id) if f.result_id else None,
        predicted_species=f.predicted_species,
        suggested_species=f.suggested_species,
        description=f.description,
        status=f.status,
        review_note=f.review_note,
        submitted_at=f.submitted_at,
        reviewed_at=f.reviewed_at,
    )


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    feedback = await FeedbackRepository.create(db, user.id, data)
    return _feedback_to_response(feedback)


@router.get("", response_model=PaginatedResponse[FeedbackResponse])
async def list_my_feedback(
    params: PageParams = Depends(),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items = await FeedbackRepository.list_by_user(
        db, user.id, status=status, offset=params.offset, limit=params.limit
    )
    total = await FeedbackRepository.count(db, status=status, user_id=user.id)
    return {
        "items": [_feedback_to_response(f) for f in items],
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.get("/inbox", response_model=PaginatedResponse[FeedbackResponse])
async def feedback_inbox(
    params: PageParams = Depends(),
    status: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    items = await FeedbackRepository.list_inbox(
        db, status=status or "pending", offset=params.offset, limit=params.limit
    )
    total = await FeedbackRepository.count(db, status=status or "pending")
    return {
        "items": [_feedback_to_response(f) for f in items],
        "total": total,
        "offset": params.offset,
        "limit": params.limit,
    }


@router.patch("/{feedback_id}", response_model=FeedbackResponse)
async def review_feedback(
    feedback_id: str,
    data: FeedbackUpdate,
    user: User = Depends(require_owner()),
    db: AsyncSession = Depends(get_db),
) -> FeedbackResponse:
    feedback = await FeedbackRepository.update_status(
        db, uuid.UUID(feedback_id), data, user.id
    )
    if not feedback:
        raise NotFoundError(f"Feedback {feedback_id} not found")
    return _feedback_to_response(feedback)


@router.post("/batch", status_code=200)
async def batch_review(
    data: FeedbackBatchRequest,
    user: User = Depends(require_owner()),
    db: AsyncSession = Depends(get_db),
) -> dict:
    updated = await FeedbackRepository.bulk_update_status(
        db,
        [uuid.UUID(fid) for fid in data.feedback_ids],
        FeedbackUpdate(status=data.status, review_note=data.review_note),
        user.id,
    )
    return {"updated": updated}
