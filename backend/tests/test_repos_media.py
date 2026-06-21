from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.exceptions import ConflictError, NotFoundError
from backend.repos import media as media_repo
from backend.schemas.media import MediaCreate, MediaUpdate


@pytest.mark.asyncio
async def test_create_media(session: AsyncSession) -> None:
    data = MediaCreate(name="Potato Dextrose Agar", description="Common fungal medium")
    result = await media_repo.create_media(session, data)
    assert result.name == "Potato Dextrose Agar"
    assert result.description == "Common fungal medium"
    assert result.is_archived is False
    assert isinstance(result.id, UUID)


@pytest.mark.asyncio
async def test_create_duplicate_media_raises(session: AsyncSession) -> None:
    data = MediaCreate(name="Malt Extract Agar")
    await media_repo.create_media(session, data)
    with pytest.raises(ConflictError, match="Malt Extract Agar"):
        await media_repo.create_media(session, data)


@pytest.mark.asyncio
async def test_get_media(session: AsyncSession) -> None:
    data = MediaCreate(name="Czapek Dox Agar", description="For Aspergillus")
    created = await media_repo.create_media(session, data)
    found = await media_repo.get_media(session, created.id)
    assert found is not None
    assert found.name == "Czapek Dox Agar"
    assert found.description == "For Aspergillus"


@pytest.mark.asyncio
async def test_get_media_nonexistent(session: AsyncSession) -> None:
    result = await media_repo.get_media(session, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_list_media(session: AsyncSession) -> None:
    names = ["MEA", "PDA", "CYA"]
    for name in names:
        await media_repo.create_media(session, MediaCreate(name=name))

    items = await media_repo.list_media(session)
    assert len(items) == 3
    assert [m.name for m in items] == sorted(names)


@pytest.mark.asyncio
async def test_list_media_archived(session: AsyncSession) -> None:
    await media_repo.create_media(session, MediaCreate(name="Active"))
    m2 = await media_repo.create_media(session, MediaCreate(name="Archived"))
    await media_repo.archive_media(session, m2.id)

    active = await media_repo.list_media(session, is_archived=False)
    archived = await media_repo.list_media(session, is_archived=True)

    assert len(active) == 1
    assert active[0].name == "Active"
    assert len(archived) == 1
    assert archived[0].name == "Archived"


@pytest.mark.asyncio
async def test_list_media_with_pagination(session: AsyncSession) -> None:
    for i in range(5):
        await media_repo.create_media(session, MediaCreate(name=f"Medium-{i}"))

    page = await media_repo.list_media(session, offset=1, limit=2)
    assert len(page) == 2
    assert page[0].name == "Medium-1"
    assert page[1].name == "Medium-2"


@pytest.mark.asyncio
async def test_count_media(session: AsyncSession) -> None:
    assert await media_repo.count_media(session) == 0
    await media_repo.create_media(session, MediaCreate(name="First"))
    await media_repo.create_media(session, MediaCreate(name="Second"))
    assert await media_repo.count_media(session) == 2


@pytest.mark.asyncio
async def test_update_media(session: AsyncSession) -> None:
    created = await media_repo.create_media(session, MediaCreate(name="Original"))
    updated = await media_repo.update_media(
        session,
        created.id,
        MediaUpdate(name="Renamed", description="Updated description"),
    )
    assert updated.name == "Renamed"
    assert updated.description == "Updated description"


@pytest.mark.asyncio
async def test_update_media_partial_name_only(session: AsyncSession) -> None:
    created = await media_repo.create_media(
        session, MediaCreate(name="Orig", description="Keep me")
    )
    updated = await media_repo.update_media(
        session, created.id, MediaUpdate(name="New Name")
    )
    assert updated.name == "New Name"
    assert updated.description == "Keep me"


@pytest.mark.asyncio
async def test_update_media_partial_description_only(session: AsyncSession) -> None:
    created = await media_repo.create_media(session, MediaCreate(name="Stick"))
    updated = await media_repo.update_media(
        session, created.id, MediaUpdate(description="New desc")
    )
    assert updated.name == "Stick"
    assert updated.description == "New desc"


@pytest.mark.asyncio
async def test_update_media_duplicate_name_raises(session: AsyncSession) -> None:
    await media_repo.create_media(session, MediaCreate(name="Existing"))
    target = await media_repo.create_media(session, MediaCreate(name="Target"))

    with pytest.raises(ConflictError, match="Existing"):
        await media_repo.update_media(session, target.id, MediaUpdate(name="Existing"))


@pytest.mark.asyncio
async def test_update_media_nonexistent_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await media_repo.update_media(session, uuid4(), MediaUpdate(name="Ghost"))


@pytest.mark.asyncio
async def test_archive_media(session: AsyncSession) -> None:
    created = await media_repo.create_media(session, MediaCreate(name="To Archive"))
    archived = await media_repo.archive_media(session, created.id)
    assert archived.is_archived is True
    assert archived.archived_at is not None

    # Verify not shown in default list (non-archived)
    active = await media_repo.list_media(session, is_archived=False)
    assert created.id not in {m.id for m in active}


@pytest.mark.asyncio
async def test_archive_media_nonexistent_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await media_repo.archive_media(session, uuid4())


@pytest.mark.asyncio
async def test_restore_media(session: AsyncSession) -> None:
    created = await media_repo.create_media(session, MediaCreate(name="Restorable"))
    await media_repo.archive_media(session, created.id)

    restored = await media_repo.restore_media(session, created.id)
    assert restored.is_archived is False
    assert restored.archived_at is None

    active = await media_repo.list_media(session, is_archived=False)
    assert restored.id in {m.id for m in active}


@pytest.mark.asyncio
async def test_restore_media_nonexistent_raises(session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await media_repo.restore_media(session, uuid4())
