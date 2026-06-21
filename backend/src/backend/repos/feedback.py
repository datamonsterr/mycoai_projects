from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Feedback, Image
from ..schemas.feedback import FeedbackCreate, FeedbackUpdate
from . import system_state


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
            result_id=(
                uuid.UUID(data.retrieval_result_id)
                if data.retrieval_result_id
                else None
            ),
            image_id=uuid.UUID(data.image_id) if data.image_id else None,
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
        feedback = await FeedbackRepository.get(db, feedback_id)
        if not feedback:
            return None
        feedback.status = data.status
        feedback.reviewer_id = reviewer_id
        feedback.review_note = data.review_note
        feedback.reviewed_at = datetime.now(UTC)

        if data.status == "accepted" and feedback.image_id:
            if feedback.feedback_type in ("wrong_prediction", "issue"):
                await db.execute(
                    update(Image)
                    .where(Image.id == feedback.image_id)
                    .values(data_update_status="pending_reindex")
                )
            elif feedback.feedback_type == "contribution":
                await db.execute(
                    update(Image)
                    .where(Image.id == feedback.image_id)
                    .values(data_update_status="pending_reference")
                )
                await system_state.increment_counter(db, "images_added")

        await db.flush()
        return feedback

    @staticmethod
    async def bulk_update_status(
        db: AsyncSession,
        feedback_ids: list[uuid.UUID],
        data: FeedbackUpdate,
        reviewer_id: uuid.UUID,
    ) -> int:
        now = datetime.now(UTC)
        stmt = (
            update(Feedback)
            .where(Feedback.id.in_(feedback_ids))
            .values(
                status=data.status,
                reviewer_id=reviewer_id,
                review_note=data.review_note,
                reviewed_at=now,
            )
        )
        await db.execute(stmt)

        if data.status == "accepted":
            feedbacks = (
                (
                    await db.execute(
                        select(Feedback).where(Feedback.id.in_(feedback_ids))
                    )
                )
                .scalars()
                .all()
            )
            reindex_image_ids = [
                f.image_id
                for f in feedbacks
                if f.image_id and f.feedback_type in ("wrong_prediction", "issue")
            ]
            reference_image_ids = [
                f.image_id
                for f in feedbacks
                if f.image_id and f.feedback_type == "contribution"
            ]
            if reindex_image_ids:
                await db.execute(
                    update(Image)
                    .where(Image.id.in_(reindex_image_ids))
                    .values(data_update_status="pending_reindex")
                )
            if reference_image_ids:
                await db.execute(
                    update(Image)
                    .where(Image.id.in_(reference_image_ids))
                    .values(data_update_status="pending_reference")
                )
                await system_state.increment_counter(
                    db, "images_added", amount=len(reference_image_ids)
                )

        await db.commit()
        return len(feedback_ids)
