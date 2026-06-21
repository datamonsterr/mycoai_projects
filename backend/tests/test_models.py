import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import Base
from backend.models import (
    AuditLog,
    Feedback,
    Image,
    InviteToken,  # noqa: F401  # registered in Base.metadata for table parity test
    Media,
    QdrantIndexState,
    RetrievalJob,
    RetrievalResult,
    Segment,
    Species,
    Strain,
    User,
)


@pytest.mark.asyncio
async def test_database_schema_creates_all_specified_tables(
    session: AsyncSession,
) -> None:
    table_names = sorted(Base.metadata.tables.keys())

    assert table_names == sorted(
        [
            "audit_log",
            "feedback",
            "images",
            "invite_tokens",
            "media",
            "qdrant_index_state",
            "refresh_tokens",
            "retrieval_jobs",
            "retrieval_neighbors",
            "retrieval_results",
            "segments",
            "species",
            "strains",
            "system_state",
            "training_jobs",
            "users",
        ]
    )


@pytest.mark.asyncio
async def test_unique_strain_name_within_species(
    session: AsyncSession,
) -> None:
    species = Species(name="Agaricus", description="Edible")
    session.add(species)
    await session.flush()
    session.add_all(
        [
            Strain(name="alpha", species_id=species.id, source="curated_primary"),
            Strain(name="alpha", species_id=species.id, source="user_upload"),
        ]
    )

    with pytest.raises(IntegrityError):
        await session.commit()


@pytest.mark.asyncio
async def test_segment_links_to_qdrant_index_state(
    session: AsyncSession,
) -> None:
    species = Species(name="Pleurotus", description=None)
    user = User(
        email="user@example.com",
        password_hash="hash",
        name="User",
    )
    media = Media(name="MEA", description=None)
    session.add_all([species, user, media])
    await session.flush()

    strain = Strain(name="st1", species_id=species.id, source="user_upload")
    session.add(strain)
    await session.flush()

    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="raw/img.jpg",
    )
    session.add(image)
    await session.flush()

    segment = Segment(
        image_id=image.id,
        segment_index=0,
        crop_path="crop/0.jpg",
        bbox_x=1,
        bbox_y=2,
        bbox_w=3,
        bbox_h=4,
        segmentation_method="kmeans",
    )
    session.add(segment)
    await session.flush()

    index_state = QdrantIndexState(
        segment_id=segment.id,
        qdrant_point_id=uuid.uuid4(),
        collection_name="segments",
    )
    session.add(index_state)
    await session.commit()

    loaded = (await session.execute(select(QdrantIndexState))).scalar_one()
    assert loaded.segment_id == segment.id


@pytest.mark.asyncio
async def test_feedback_and_audit_relations(
    session: AsyncSession,
) -> None:
    user = User(email="u@example.com", password_hash="hash", name="U")
    session.add(user)
    await session.flush()

    job = RetrievalJob(user_id=user.id, job_type="single", config={"k": 5})
    session.add(job)
    await session.flush()

    result = RetrievalResult(
        job_id=job.id,
        strain_name="strain-a",
        rank=1,
        species_name="species-a",
        score=0.8,
    )
    session.add(result)
    await session.flush()

    feedback = Feedback(
        submitter_id=user.id,
        source="query_result",
        result_id=result.id,
        suggested_species="species-b",
        description="wrong label",
    )
    audit = AuditLog(
        user_id=user.id,
        action="accept_feedback",
        entity_type="feedback",
        entity_id=feedback.id,
        changes={"status": {"old": "pending", "new": "accepted"}},
    )
    session.add_all([feedback, audit])
    await session.commit()

    stored_feedback = (await session.execute(select(Feedback))).scalar_one()
    assert stored_feedback.source == "query_result"
    assert stored_feedback.status == "pending"
