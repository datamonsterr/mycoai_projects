from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import CurrentOwner
from ..database import get_db
from ..models import Feedback, Image, TrainingJob
from ..repos import system_state
from ..schemas.index import (
    IndexStatusResponse,
    ReindexRequest,
    ReindexStatus,
    RetrainingCounter,
    RetrainingStatus,
)

router = APIRouter()


@router.post("/reindex", status_code=202)
async def trigger_reindex(
    data: ReindexRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
) -> dict:
    job = TrainingJob(
        triggered_by=current_owner.id,
        job_type="qdrant_reindex",
        status="pending",
        config={"scope": data.scope},
    )
    db.add(job)
    await db.flush()
    return {
        "job_id": str(job.id),
        "status": job.status,
        "scope": data.scope,
    }


@router.get("/status", response_model=IndexStatusResponse)
async def get_index_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
) -> IndexStatusResponse:
    # Re-index metrics
    items_updated_result = await db.execute(
        select(func.count(Image.id)).where(
            Image.data_update_status == "updated_requires_reindex"
        )
    )
    items_updated = items_updated_result.scalar() or 0

    items_archived_result = await db.execute(
        select(func.count(Image.id)).where(Image.is_archived.is_(True))
    )
    items_archived = items_archived_result.scalar() or 0

    feedback_accepted_result = await db.execute(
        select(func.count(Feedback.id)).where(Feedback.status == "accepted")
    )
    feedback_accepted = feedback_accepted_result.scalar() or 0

    contributions_result = await db.execute(
        select(func.count(Feedback.id)).where(
            Feedback.status == "accepted",
            Feedback.feedback_type == "contribution",
        )
    )
    contributions_accepted = contributions_result.scalar() or 0

    reindex_status_str = "current"
    if items_updated > 0 or items_archived > 0:
        reindex_status_str = "needs_reindex"

    reindex = ReindexStatus(
        status=reindex_status_str,
        items_updated=items_updated,
        items_archived=items_archived,
        feedback_accepted=feedback_accepted,
        contributions_accepted=contributions_accepted,
    )

    # Retraining metrics
    counter_data = await system_state.get_counter(db)
    threshold = await system_state.get_threshold(db)
    total_changes = sum(
        counter_data.get(f, 0) for f in ("images_added", "bbox_corrections", "items_archived", "species_added")
    )

    retraining_counter = RetrainingCounter(
        images_added=counter_data.get("images_added", 0),
        bbox_corrections=counter_data.get("bbox_corrections", 0),
        items_archived=counter_data.get("items_archived", 0),
        species_added=counter_data.get("species_added", 0),
        last_reset_at=counter_data.get("last_reset_at"),
    )

    retraining = RetrainingStatus(
        counter=retraining_counter,
        threshold=threshold,
        warning_active=total_changes > threshold,
        last_training_completed_at=counter_data.get("last_reset_at"),
    )

    # Current model version (from latest deployed training job or fallback)
    current_version = "efficientnet-b1-v3"
    latest_job_result = await db.execute(
        select(TrainingJob)
        .where(TrainingJob.is_deployed.is_(True))
        .order_by(TrainingJob.completed_at.desc())
        .limit(1)
    )
    latest_job = latest_job_result.scalar_one_or_none()
    if latest_job and latest_job.model_version:
        current_version = latest_job.model_version

    return IndexStatusResponse(
        reindex=reindex,
        retraining=retraining,
        current_model_version=current_version,
    )


@router.post("/training-complete", status_code=200)
async def acknowledge_training_complete(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
) -> dict:
    counter = await system_state.reset_counter(db)
    return {
        "message": "Retraining counter reset",
        "counter": counter,
    }
