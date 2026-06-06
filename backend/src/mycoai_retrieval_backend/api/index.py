from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import CurrentOwner
from ..database import get_db
from ..models import TrainingJob
from ..schemas.index import IndexStatusResponse, ReindexRequest

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
    return IndexStatusResponse(
        qdrant_index_status="healthy",
        changes_since_last={},
        external_retraining_recommended=False,
    )
