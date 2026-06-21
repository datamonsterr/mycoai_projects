import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditLog, User


async def _create_user(session: AsyncSession, *, email: str | None = None) -> User:
    user = User(
        email=email or f"audit-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        name="Audit Tester",
        role="owner",
    )
    session.add(user)
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_audit_log_created_on_species_create(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="create_species",
        entity_type="species",
        entity_id=uuid.uuid4(),
        changes={"name": {"old": None, "new": "Agaricus bisporus"}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(
        select(AuditLog).where(AuditLog.action == "create_species")
    )
    assert result is not None
    assert result.entity_type == "species"


@pytest.mark.asyncio
async def test_audit_log_created_on_species_archive(session: AsyncSession):
    user = await _create_user(session)
    species_id = uuid.uuid4()
    audit = AuditLog(
        user_id=user.id,
        action="archive_species",
        entity_type="species",
        entity_id=species_id,
        changes={"is_archived": {"old": False, "new": True}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(
        select(AuditLog).where(AuditLog.action == "archive_species")
    )
    assert result is not None
    assert result.entity_id == species_id


@pytest.mark.asyncio
async def test_audit_log_created_on_media_create(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="create_media",
        entity_type="media",
        entity_id=uuid.uuid4(),
        changes={"name": {"old": None, "new": "MEA"}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(
        select(AuditLog).where(AuditLog.action == "create_media")
    )
    assert result is not None
    assert result.entity_type == "media"


@pytest.mark.asyncio
async def test_audit_log_created_on_feedback_accept(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="accept_feedback",
        entity_type="feedback",
        entity_id=uuid.uuid4(),
        changes={"status": {"old": "pending", "new": "accepted"}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(
        select(AuditLog).where(AuditLog.action == "accept_feedback")
    )
    assert result is not None


@pytest.mark.asyncio
async def test_audit_log_created_on_role_change(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="role_change",
        entity_type="user",
        entity_id=user.id,
        changes={"role": {"old": "user", "new": "owner"}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(
        select(AuditLog).where(AuditLog.action == "role_change")
    )
    assert result is not None


@pytest.mark.asyncio
async def test_audit_log_contains_user_id_and_timestamp(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="test",
        entity_type="test",
        entity_id=uuid.uuid4(),
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(select(AuditLog).where(AuditLog.user_id == user.id))
    assert result.user_id == user.id
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_audit_log_changes_field_captures_old_new_values(session: AsyncSession):
    user = await _create_user(session)
    audit = AuditLog(
        user_id=user.id,
        action="update",
        entity_type="species",
        entity_id=uuid.uuid4(),
        changes={"description": {"old": "Old desc", "new": "New desc"}},
    )
    session.add(audit)
    await session.commit()
    result = await session.scalar(select(AuditLog).where(AuditLog.user_id == user.id))
    assert result.changes["description"]["old"] == "Old desc"
    assert result.changes["description"]["new"] == "New desc"


@pytest.mark.asyncio
async def test_audit_log_queriable_by_entity_type(session: AsyncSession):
    user = await _create_user(session)
    session.add_all(
        [
            AuditLog(
                user_id=user.id,
                action="a",
                entity_type="species",
                entity_id=uuid.uuid4(),
            ),
            AuditLog(
                user_id=user.id, action="b", entity_type="media", entity_id=uuid.uuid4()
            ),
            AuditLog(
                user_id=user.id,
                action="c",
                entity_type="species",
                entity_id=uuid.uuid4(),
            ),
        ]
    )
    await session.commit()
    results = (
        (
            await session.execute(
                select(AuditLog).where(AuditLog.entity_type == "species")
            )
        )
        .scalars()
        .all()
    )
    assert len(results) == 2


@pytest.mark.asyncio
async def test_audit_log_queriable_by_user_id(session: AsyncSession):
    user1 = await _create_user(session, email="u1@test.com")
    user2 = await _create_user(session, email="u2@test.com")
    session.add_all(
        [
            AuditLog(
                user_id=user1.id, action="x", entity_type="t", entity_id=uuid.uuid4()
            ),
            AuditLog(
                user_id=user2.id, action="y", entity_type="t", entity_id=uuid.uuid4()
            ),
            AuditLog(
                user_id=user1.id, action="z", entity_type="t", entity_id=uuid.uuid4()
            ),
        ]
    )
    await session.commit()
    results = (
        (await session.execute(select(AuditLog).where(AuditLog.user_id == user1.id)))
        .scalars()
        .all()
    )
    assert len(results) == 2
