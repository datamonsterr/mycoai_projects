import uuid as _uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_qdrant_settings, get_storage_settings
from ..core.dependencies import CurrentOwner, CurrentUser
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
from ..services.storage import create_storage

router = APIRouter()


@router.post("/reindex", status_code=202)
async def trigger_reindex(
    data: ReindexRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
) -> dict:
    import datetime
    import logging
    import uuid

    from sqlalchemy.orm import selectinload

    from ..models import QdrantIndexState, Segment
    from ..services.feature_extraction import extract_features
    from ..services.qdrant_client import QdrantClientService

    logger = logging.getLogger(__name__)

    job = TrainingJob(
        triggered_by=current_owner.id,
        job_type="qdrant_reindex",
        status="processing",
        progress={"scope": data.scope},
        started_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(job)
    await db.flush()

    # Find unindexed segments (qdrant_point_id IS NULL)
    stmt = (
        select(Segment)
        .options(selectinload(Segment.image))
        .where(Segment.qdrant_point_id.is_(None))
        .where(Segment.is_archived.is_(False))
    )

    result = await db.execute(stmt)
    segments = list(result.unique().scalars().all())

    indexed = 0
    errors: list[dict] = []

    qdrant_svc = QdrantClientService()
    collection_name = get_qdrant_settings().collection_name
    storage = create_storage(get_storage_settings())

    for seg in segments:
        try:
            crop_path = Path(seg.crop_path)
            crop_key = str(crop_path)
            crop_data = None

            if crop_path.exists():
                crop_data = crop_path.read_bytes()
            else:
                crop_data = storage.get_bytes(crop_key)
                if crop_data is None:
                    relative_key = str(Path(*crop_path.parts[-3:]))
                    crop_data = storage.get_bytes(relative_key)

            if crop_data is None:
                errors.append(
                    {"segment_id": str(seg.id), "error": "crop file not found"}
                )
                continue

            tmp = Path(f"/tmp/opencode/reindex_{seg.id}.jpg")
            tmp.write_bytes(crop_data)
            vectors = extract_features(tmp)
            tmp.unlink(missing_ok=True)
            if not vectors:
                continue

            point_id = _uuid.uuid4().int & ((1 << 63) - 1)
            await qdrant_svc.upsert_point(
                point_id=point_id,
                vectors=vectors,
                payload={
                    "segment_id": str(seg.id),
                    "image_id": str(seg.image_id),
                    "segment_index": seg.segment_index,
                    "bbox": {
                        "x": seg.bbox_x,
                        "y": seg.bbox_y,
                        "w": seg.bbox_w,
                        "h": seg.bbox_h,
                    },
                },
            )

            seg.qdrant_point_id = uuid.UUID(int=point_id)

            qis = QdrantIndexState(
                segment_id=seg.id,
                qdrant_point_id=seg.qdrant_point_id,
                collection_name=collection_name,
                is_active=True,
            )
            db.add(qis)
            indexed += 1

        except Exception as exc:
            logger.error(f"Index failed for segment {seg.id}: {exc}")
            errors.append({"segment_id": str(seg.id), "error": str(exc)})

    job.status = "completed"
    job.completed_at = datetime.datetime.now(datetime.UTC)
    await db.commit()

    return {
        "job_id": str(job.id),
        "status": "completed",
        "scope": data.scope,
        "total": len(segments),
        "indexed": indexed,
        "errors": len(errors),
    }


@router.get("/status", response_model=IndexStatusResponse)
async def get_index_status(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
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
        counter_data.get(f, 0)
        for f in ("images_added", "bbox_corrections", "items_archived", "species_added")
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
