import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Media
from ..schemas.media import MediaCreate, MediaUpdate


async def create_media(db: AsyncSession, data: MediaCreate) -> Media:
    existing = await db.execute(select(Media).where(Media.name == data.name))
    if existing.scalar_one_or_none():
        from ..core.exceptions import ConflictError

        raise ConflictError(f"Media '{data.name}' already exists")

    media = Media(name=data.name, description=data.description)
    db.add(media)
    await db.commit()
    await db.refresh(media)
    return media


async def get_media(db: AsyncSession, media_id: UUID) -> Media | None:
    result = await db.execute(select(Media).where(Media.id == media_id))
    return result.scalar_one_or_none()


async def list_media(
    db: AsyncSession,
    is_archived: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[Media]:
    result = await db.execute(
        select(Media)
        .where(Media.is_archived == is_archived)
        .order_by(Media.name)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_media(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Media))
    return result.scalar() or 0


async def update_media(db: AsyncSession, media_id: UUID, data: MediaUpdate) -> Media:
    from ..core.exceptions import NotFoundError

    media = await get_media(db, media_id)
    if not media:
        raise NotFoundError(f"Media {media_id} not found")

    if data.name is not None and data.name != media.name:
        existing = await db.execute(
            select(Media).where(Media.name == data.name, Media.id != media_id)
        )
        if existing.scalar_one_or_none():
            from ..core.exceptions import ConflictError

            raise ConflictError(f"Media '{data.name}' already exists")
        media.name = data.name
    if data.description is not None:
        media.description = data.description
    media.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(media)
    return media


async def archive_media(db: AsyncSession, media_id: UUID) -> Media:
    from ..core.exceptions import NotFoundError

    media = await get_media(db, media_id)
    if not media:
        raise NotFoundError(f"Media {media_id} not found")
    media.is_archived = True
    media.archived_at = datetime.datetime.now(datetime.UTC)
    media.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(media)
    return media


async def restore_media(db: AsyncSession, media_id: UUID) -> Media:
    from ..core.exceptions import NotFoundError

    media = await get_media(db, media_id)
    if not media:
        raise NotFoundError(f"Media {media_id} not found")
    media.is_archived = False
    media.archived_at = None
    media.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(media)
    return media
