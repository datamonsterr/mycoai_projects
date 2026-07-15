from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_storage_settings
from ..models import Feedback, Image, Segment, Species
from ..qdrant import delete_points, get_qdrant_client
from ..schemas.feedback import FeedbackCreate, FeedbackUpdate
from ..services.storage import create_storage, storage_candidates
from . import system_state

TEMPORARY_QUERY_STATUS = "temporary_query"
TEMPORARY_QUERY_SOURCE = "temporary_query"


async def _ensure_species(db: AsyncSession, name: str) -> Species:
    result = await db.execute(select(Species).where(Species.name == name))
    species = result.scalar_one_or_none()
    if species is not None:
        return species
    species = Species(name=name)
    db.add(species)
    await db.flush()
    return species


async def _delete_image_runtime(db: AsyncSession, image: Image) -> None:
    points_by_collection: dict[str, list[int]] = {}
    for segment in image.segments:
        state = segment.qdrant_index_state
        if state is not None:
            points_by_collection.setdefault(state.collection_name, []).append(
                state.qdrant_point_id.int
            )
            await db.delete(state)
        elif segment.qdrant_point_id is not None:
            points_by_collection.setdefault("", []).append(segment.qdrant_point_id.int)
        segment.qdrant_point_id = None

    if points_by_collection:
        qdrant = get_qdrant_client()
        for collection_name, point_ids in points_by_collection.items():
            delete_points(qdrant, point_ids, collection_name=collection_name or None)

    settings = get_storage_settings()
    storage = create_storage(settings)
    upload_root = Path(settings.upload_root)
    if not upload_root.is_absolute():
        upload_root = (Path.cwd() / upload_root).resolve()
    for path in [image.file_path, image.prepared_path, image.pipeline_path]:
        if not path:
            continue
        for key in storage_candidates(path, upload_root=upload_root):
            if storage.object_exists(key):
                storage.delete(key)
                break
    for segment in image.segments:
        for key in storage_candidates(segment.crop_path, upload_root=upload_root):
            if storage.object_exists(key):
                storage.delete(key)
                break

    await db.delete(image)


class FeedbackRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        submitter_id: uuid.UUID,
        data: FeedbackCreate,
    ) -> Feedback:
        feedback = Feedback(
            submitter_id=submitter_id,
            source="retrieval_result",
            feedback_type=data.feedback_type,
            query_strain=data.query_strain,
            result_id=data.retrieval_result_id,
            image_id=data.image_id,
            predicted_species=data.predicted_species,
            suggested_species=data.suggested_species or "",
            description=data.description,
            status="pending",
            submitted_at=datetime.now(UTC),
        )
        db.add(feedback)
        await db.commit()
        return feedback

    @staticmethod
    async def get(db: AsyncSession, feedback_id: uuid.UUID) -> Feedback | None:
        result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def list_by_user(
        db: AsyncSession,
        user_id: uuid.UUID,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Feedback]:
        stmt = select(Feedback).where(Feedback.submitter_id == user_id)
        if status:
            stmt = stmt.where(Feedback.status == status)
        stmt = stmt.order_by(Feedback.submitted_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def list_inbox(
        db: AsyncSession,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Feedback]:
        stmt = select(Feedback)
        if status:
            stmt = stmt.where(Feedback.status == status)
        stmt = stmt.order_by(Feedback.submitted_at.asc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count(
        db: AsyncSession,
        status: str | None = None,
        user_id: uuid.UUID | None = None,
    ) -> int:
        from sqlalchemy import func

        stmt = select(func.count(Feedback.id))
        if user_id is not None:
            stmt = stmt.where(Feedback.submitter_id == user_id)
        if status:
            stmt = stmt.where(Feedback.status == status)
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        feedback_id: uuid.UUID,
        data: FeedbackUpdate,
        reviewer_id: uuid.UUID,
    ) -> Feedback | None:
        result = await db.execute(
            select(Feedback)
            .options(
                selectinload(Feedback.image).selectinload(Image.strain),
                selectinload(Feedback.image)
                .selectinload(Image.segments)
                .selectinload(Segment.qdrant_index_state)
            )
            .where(Feedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            return None

        image = feedback.image
        is_temporary_query = (
            image is not None
            and (
                image.source_type == TEMPORARY_QUERY_SOURCE
                or image.data_update_status == TEMPORARY_QUERY_STATUS
            )
        )

        if data.status == "rejected" and is_temporary_query and image is not None:
            await _delete_image_runtime(db, image)
            await db.delete(feedback)
            await db.commit()
            return feedback

        feedback.status = data.status
        feedback.reviewer_id = reviewer_id
        feedback.review_note = data.review_note
        feedback.reviewed_at = datetime.now(UTC)

        if data.status == "accepted" and image is not None:
            if is_temporary_query:
                image.source_type = "dataset"
                if feedback.suggested_species:
                    species = await _ensure_species(db, feedback.suggested_species)
                    image.species_id = species.id
                    if image.strain is not None:
                        image.strain.species_id = species.id
            if feedback.feedback_type in ("wrong_prediction", "issue"):
                image.data_update_status = "updated_requires_reindex"
            elif feedback.feedback_type == "contribution":
                image.data_update_status = "pending_reference"
                await system_state.increment_counter(db, "images_added")

        await db.commit()
        return feedback

    @staticmethod
    async def bulk_update_status(
        db: AsyncSession,
        feedback_ids: list[uuid.UUID],
        data: FeedbackUpdate,
        reviewer_id: uuid.UUID,
    ) -> int:
        updated = 0
        for feedback_id in feedback_ids:
            feedback = await FeedbackRepository.update_status(
                db, feedback_id, data, reviewer_id
            )
            if feedback is not None:
                updated += 1
        return updated
