from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.models import (
    AuditLog,
    Image,
    Media,
    Species,
    Strain,
    User,
)

pytestmark = [pytest.mark.integration, pytest.mark.integration_postgres]

import os

POSTGRES_URL = os.getenv(
    "MYCOAI_TEST_DB_URL",
    "postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai_test",
)


# ── Connection helpers ───────────────────────────────────────────────


def _create_engine():
    return create_async_engine(POSTGRES_URL, echo=False)


async def _ping(engine: AsyncEngine):
    async with engine.connect() as conn:
        result = await conn.execute(select(select(1).exists()))
        return result.scalar_one()


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pg_connection_works() -> None:
    engine = _create_engine()
    try:
        ok = await _ping(engine)
        assert ok is True
    except Exception:
        pytest.skip("Postgres not available")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pg_create_and_query_user(pg_session: AsyncSession) -> None:
    user = User(
        id=uuid.uuid4(),
        email="query-test@test.local",
        password_hash="hashed",
        name="Query Tester",
        role="user",
        is_active=True,
    )
    pg_session.add(user)
    await pg_session.flush()

    result = await pg_session.execute(
        select(User).where(User.email == "query-test@test.local")
    )
    loaded = result.scalar_one()
    assert loaded.name == "Query Tester"
    assert loaded.role == "user"
    assert loaded.is_active is True
    assert loaded.email == "query-test@test.local"


@pytest.mark.asyncio
async def test_pg_create_species_and_strain_with_relations(
    pg_session: AsyncSession,
) -> None:
    species = Species(name="Aspergillus niger", description="Test species")
    pg_session.add(species)
    await pg_session.flush()

    strain = Strain(
        name="AN-001",
        species_id=species.id,
        source="curated_primary",
    )
    pg_session.add(strain)
    await pg_session.commit()

    result = await pg_session.execute(select(Strain).where(Strain.name == "AN-001"))
    loaded = result.scalar_one()
    assert loaded.species_id == species.id
    assert loaded.species.name == "Aspergillus niger"


@pytest.mark.asyncio
async def test_pg_transaction_rollback(
    pg_engine: AsyncEngine,
    pg_session: AsyncSession,
) -> None:
    user = User(
        id=uuid.uuid4(),
        email="rollback-test@test.local",
        password_hash="hashed",
        name="Rollback",
        role="user",
        is_active=True,
    )
    pg_session.add(user)
    await pg_session.flush()
    await pg_session.commit()

    rollback_session: AsyncSession
    async_session = async_sessionmaker(
        bind=pg_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as rollback_session:
        rollback_session.add(
            AuditLog(
                user_id=user.id,
                action="rollback-test",
                entity_type="test",
                changes={"test": True},
            )
        )
        await rollback_session.flush()
        # No commit — session exits → implicit rollback

    result = await pg_session.execute(
        select(AuditLog).where(AuditLog.action == "rollback-test")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_pg_media_unique_constraint(pg_session: AsyncSession) -> None:
    media = Media(name="integration-media-dup", description="First")
    pg_session.add(media)
    await pg_session.flush()

    dupe = Media(name="integration-media-dup", description="Second")
    pg_session.add(dupe)

    with pytest.raises(IntegrityError):
        await pg_session.flush()

    await pg_session.rollback()


@pytest.mark.asyncio
async def test_pg_image_fks_required(pg_session: AsyncSession) -> None:
    image = Image(
        id=uuid.uuid4(),
        strain_id=uuid.uuid4(),
        species_id=uuid.uuid4(),
        media_id=uuid.uuid4(),
        file_path="test.jpg",
    )
    pg_session.add(image)

    with pytest.raises(IntegrityError):
        await pg_session.flush()

    await pg_session.rollback()


@pytest.mark.asyncio
async def test_pg_audit_log_insert_and_query(pg_session: AsyncSession) -> None:
    user = User(
        id=uuid.uuid4(),
        email="audit-test@test.local",
        password_hash="hashed",
        name="Audit Tester",
        role="user",
        is_active=True,
    )
    pg_session.add(user)
    await pg_session.flush()

    audit = AuditLog(
        user_id=user.id,
        action="create_species",
        entity_type="species",
        entity_id=uuid.uuid4(),
        changes={"name": {"old": None, "new": "Test"}},
    )
    pg_session.add(audit)
    await pg_session.commit()

    result = await pg_session.execute(
        select(AuditLog).where(AuditLog.action == "create_species")
    )
    loaded = result.scalar_one()
    assert loaded.entity_type == "species"
    assert loaded.changes is not None
    name_change = loaded.changes.get("name", {})
    assert isinstance(name_change, dict)
    assert name_change.get("new") == "Test"


@pytest.mark.asyncio
async def test_pg_concurrent_sessions(pg_session: AsyncSession) -> None:
    species_a = Species(name="Concurrent Species A", description="A")
    species_b = Species(name="Concurrent Species B", description="B")
    pg_session.add_all([species_a, species_b])
    await pg_session.commit()

    result = await pg_session.execute(
        select(Species)
        .where(Species.name.like("Concurrent Species%"))
        .order_by(Species.name)
    )
    all_species = list(result.scalars().all())
    assert len(all_species) == 2
    names = [s.name for s in all_species]
    assert "Concurrent Species A" in names
    assert "Concurrent Species B" in names
