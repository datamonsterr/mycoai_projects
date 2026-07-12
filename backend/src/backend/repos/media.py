import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ..models import Image, Media, Segment, Strain
from ..schemas.media import MediaCreate, MediaUpdate


def _normalize_media_name(name: str) -> str:
    return name.strip().upper()


async def create_media(db: AsyncSession, data: MediaCreate) -> Media:
    normalized_name = _normalize_media_name(data.name)
    existing = await db.execute(select(Media).where(Media.name == normalized_name))
    if existing.scalar_one_or_none():
        from ..core.exceptions import ConflictError

        raise ConflictError(f"Media '{normalized_name}' already exists")

    media = Media(name=normalized_name, description=data.description)
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

    if data.name is not None:
        normalized_name = _normalize_media_name(data.name)
        if normalized_name != media.name:
            existing = await db.execute(
                select(Media).where(Media.name == normalized_name, Media.id != media_id)
            )
            if existing.scalar_one_or_none():
                from ..core.exceptions import ConflictError

                raise ConflictError(f"Media '{normalized_name}' already exists")
            media.name = normalized_name
    if data.description is not None:
        media.description = data.description
    media.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(media)
    return media


async def delete_impact_media(db: AsyncSession, media_id: UUID) -> tuple[int, int]:
    strain_alias = aliased(Strain)
    strain_result = await db.execute(
        select(func.count(func.distinct(Image.strain_id)))
        .select_from(Image)
        .where(Image.media_id == media_id)
    )
    segment_result = await db.execute(
        select(func.count(Segment.id))
        .select_from(Segment)
        .join(Image, Segment.image_id == Image.id)
        .join(strain_alias, Image.strain_id == strain_alias.id)
        .where(
            Image.media_id == media_id,
            Image.is_archived.is_(False),
            Segment.is_archived.is_(False),
            strain_alias.is_archived.is_(False),
        )
    )
    return strain_result.scalar() or 0, segment_result.scalar() or 0


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


async def clean_media(db: AsyncSession, media_id: UUID) -> None:
    from ..core.exceptions import NotFoundError

    media = await get_media(db, media_id)
    if not media:
        raise NotFoundError(f"Media {media_id} not found")

    segment_ids = await db.execute(
        select(Segment.id)
        .join(Image, Segment.image_id == Image.id)
        .where(Image.media_id == media_id)
    )
    await db.execute(
        delete(Segment).where(Segment.id.in_(list(segment_ids.scalars().all())))
    )
    await db.execute(delete(Image).where(Image.media_id == media_id))
    await db.delete(media)
    await db.commit()
