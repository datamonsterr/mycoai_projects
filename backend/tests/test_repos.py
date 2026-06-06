from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mycoai_retrieval_backend.models import (
    Feedback,
    Media,
    RefreshToken,
    RetrievalJob,
    Species,
    User,
)

# ── Species ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_species(session: AsyncSession) -> None:
    species = Species(name="Cladosporium herbarum", description="Common mold")
    session.add(species)
    await session.commit()

    result = (
        await session.execute(
            select(Species).where(Species.name == "Cladosporium herbarum")
        )
    ).scalar_one()
    assert result.name == "Cladosporium herbarum"
    assert result.description == "Common mold"
    assert result.is_archived is False


@pytest.mark.asyncio
async def test_list_species_with_offset_limit(session: AsyncSession) -> None:
    for i in range(10):
        session.add(Species(name=f"Species-{i}"))
    await session.commit()

    page = (
        (
            await session.execute(
                select(Species).order_by(Species.name).offset(3).limit(4)
            )
        )
        .scalars()
        .all()
    )
    assert len(page) == 4
    assert page[0].name == "Species-3"


@pytest.mark.asyncio
async def test_archive_species(session: AsyncSession) -> None:
    species = Species(name="Deletable Species")
    session.add(species)
    await session.commit()

    stored = (
        await session.execute(
            select(Species).where(Species.name == "Deletable Species")
        )
    ).scalar_one()
    stored.is_archived = True
    stored.archived_at = datetime.now(UTC)
    await session.commit()

    reloaded = (
        await session.execute(
            select(Species).where(Species.name == "Deletable Species")
        )
    ).scalar_one()
    assert reloaded.is_archived is True
    assert reloaded.archived_at is not None


@pytest.mark.asyncio
async def test_restore_species(session: AsyncSession) -> None:
    species = Species(
        name="Restorable Species", is_archived=True, archived_at=datetime.now(UTC)
    )
    session.add(species)
    await session.commit()

    stored = (
        await session.execute(
            select(Species).where(Species.name == "Restorable Species")
        )
    ).scalar_one()
    stored.is_archived = False
    stored.archived_at = None
    await session.commit()

    restored = (
        await session.execute(
            select(Species).where(Species.name == "Restorable Species")
        )
    ).scalar_one()
    assert restored.is_archived is False
    assert restored.archived_at is None


# ── Media ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_and_get_media(session: AsyncSession) -> None:
    media = Media(
        name="DG18-Dichloran Glycerol", description="Low water activity medium"
    )
    session.add(media)
    await session.commit()

    loaded = (
        await session.execute(
            select(Media).where(Media.name == "DG18-Dichloran Glycerol")
        )
    ).scalar_one()
    assert loaded.name == "DG18-Dichloran Glycerol"
    assert loaded.is_archived is False


@pytest.mark.asyncio
async def test_list_media_with_archived_filter(session: AsyncSession) -> None:
    media1 = Media(name="Active Medium")
    media2 = Media(name="Archived Medium", is_archived=True)
    session.add_all([media1, media2])
    await session.commit()

    active = (
        (await session.execute(select(Media).where(Media.is_archived == False)))
        .scalars()
        .all()
    )
    archived = (
        (await session.execute(select(Media).where(Media.is_archived == True)))
        .scalars()
        .all()
    )

    assert len(active) == 1
    assert active[0].name == "Active Medium"
    assert len(archived) == 1
    assert archived[0].name == "Archived Medium"


# ── Feedback ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_feedback(session: AsyncSession) -> None:
    user = User(email="fb@test.com", password_hash="h", name="FB User")
    session.add(user)
    await session.flush()

    feedback = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="Penicillium expansum",
        description="Looks like P. expansum",
    )
    session.add(feedback)
    await session.commit()

    loaded = (await session.execute(select(Feedback))).scalar_one()
    assert loaded.status == "pending"
    assert loaded.suggested_species == "Penicillium expansum"


@pytest.mark.asyncio
async def test_list_inbox_by_status(session: AsyncSession) -> None:
    user = User(email="inbox@test.com", password_hash="h", name="Inbox User")
    session.add(user)
    await session.flush()

    f1 = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="A",
        description="d1",
        status="pending",
    )
    f2 = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="B",
        description="d2",
        status="accepted",
    )
    session.add_all([f1, f2])
    await session.commit()

    pending = (
        (await session.execute(select(Feedback).where(Feedback.status == "pending")))
        .scalars()
        .all()
    )
    accepted = (
        (await session.execute(select(Feedback).where(Feedback.status == "accepted")))
        .scalars()
        .all()
    )

    assert len(pending) == 1
    assert pending[0].suggested_species == "A"
    assert len(accepted) == 1
    assert accepted[0].suggested_species == "B"


@pytest.mark.asyncio
async def test_update_feedback_status(session: AsyncSession) -> None:
    user = User(email="status@test.com", password_hash="h", name="Status User")
    session.add(user)
    await session.flush()

    fb = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="P. commune",
        description="d",
    )
    session.add(fb)
    await session.commit()

    fb.status = "accepted"
    fb.reviewer_id = user.id
    fb.reviewed_at = datetime.now(UTC)
    await session.commit()

    updated = (await session.execute(select(Feedback))).scalar_one()
    assert updated.status == "accepted"
    assert updated.reviewer_id == user.id
    assert updated.reviewed_at is not None


@pytest.mark.asyncio
async def test_bulk_update_feedback(session: AsyncSession) -> None:
    user = User(email="bulk@test.com", password_hash="h", name="Bulk User")
    session.add(user)
    await session.flush()

    f1 = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="A",
        description="d1",
    )
    f2 = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="B",
        description="d2",
    )
    f3 = Feedback(
        submitter_id=user.id,
        source="query_result",
        suggested_species="C",
        description="d3",
    )
    session.add_all([f1, f2, f3])
    await session.commit()

    ids_to_update = [f1.id, f2.id]
    stmt = select(Feedback).where(Feedback.id.in_(ids_to_update))
    targets = (await session.execute(stmt)).scalars().all()
    for f in targets:
        f.status = "rejected"
    await session.commit()

    rejected = (
        (await session.execute(select(Feedback).where(Feedback.status == "rejected")))
        .scalars()
        .all()
    )
    assert len(rejected) == 2


# ── Users ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_users_by_role(session: AsyncSession) -> None:
    u1 = User(email="o1@test.com", password_hash="h", name="Owner1", role="owner")
    u2 = User(email="u1@test.com", password_hash="h", name="User1", role="user")
    u3 = User(email="u2@test.com", password_hash="h", name="User2", role="user")
    session.add_all([u1, u2, u3])
    await session.commit()

    owners = (
        (await session.execute(select(User).where(User.role == "owner")))
        .scalars()
        .all()
    )
    users = (
        (await session.execute(select(User).where(User.role == "user"))).scalars().all()
    )

    owner_emails = {o.email for o in owners}
    assert "o1@test.com" in owner_emails
    assert len(users) == 3


@pytest.mark.asyncio
async def test_count_active_owners(session: AsyncSession) -> None:
    session.add(
        User(
            email="active_o@test.com",
            password_hash="h",
            name="Active O",
            role="owner",
            is_active=True,
        )
    )
    session.add(
        User(
            email="inactive_o@test.com",
            password_hash="h",
            name="Inactive O",
            role="owner",
            is_active=False,
        )
    )
    await session.commit()

    count = (
        await session.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "owner", User.is_active == True)
        )
    ).scalar_one()
    assert count == 2


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession) -> None:
    user = User(
        email="create@test.com", password_hash="bcrypt_hash", name="Created User"
    )
    session.add(user)
    await session.commit()

    loaded = (
        await session.execute(select(User).where(User.email == "create@test.com"))
    ).scalar_one()
    assert loaded.name == "Created User"
    assert loaded.role == "user"
    assert loaded.is_active is True


@pytest.mark.asyncio
async def test_get_user_by_id(session: AsyncSession) -> None:
    user = User(email="byid@test.com", password_hash="h", name="ByID User")
    session.add(user)
    await session.commit()

    loaded = (
        await session.execute(select(User).where(User.id == user.id))
    ).scalar_one()
    assert loaded.email == "byid@test.com"


# ── Refresh Token ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_refresh_token(session: AsyncSession) -> None:
    user = User(email="rt@test.com", password_hash="h", name="RT User")
    session.add(user)
    await session.flush()

    expires = datetime.now(UTC)
    rt = RefreshToken(
        user_id=user.id, token_hash="hashed_token_value", expires_at=expires
    )
    session.add(rt)
    await session.commit()

    loaded = (await session.execute(select(RefreshToken))).scalar_one()
    assert loaded.user_id == user.id
    assert loaded.token_hash == "hashed_token_value"
    assert loaded.expires_at == expires


# ── Retrieval Job ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_retrieval_job(session: AsyncSession) -> None:
    user = User(email="rj@test.com", password_hash="h", name="RJ User")
    session.add(user)
    await session.flush()

    job = RetrievalJob(
        user_id=user.id,
        job_type="batch",
        config={"k": 5, "aggregation": "weighted"},
    )
    session.add(job)
    await session.commit()

    loaded = (await session.execute(select(RetrievalJob))).scalar_one()
    assert loaded.user_id == user.id
    assert loaded.job_type == "batch"
    assert loaded.status == "pending"
    assert loaded.config == {"k": 5, "aggregation": "weighted"}
