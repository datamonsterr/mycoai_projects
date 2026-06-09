from __future__ import annotations

import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Image
from . import system_state


async def get_image(db: AsyncSession, image_id: UUID) -> Image | None:
    result = await db.execute(select(Image).where(Image.id == image_id))
    return result.scalar_one_or_none()


async def archive_image(db: AsyncSession, image_id: UUID) -> Image:
    from ..core.exceptions import NotFoundError

    image = await get_image(db, image_id)
    if not image:
        raise NotFoundError(f"Image {image_id} not found")

    image.is_archived = True
    image.archived_at = datetime.datetime.now(datetime.UTC)
    image.updated_at = datetime.datetime.now(datetime.UTC)
    image.data_update_status = "archived"
    await db.flush()
    await system_state.increment_counter(db, "items_archived")
    return image


async def restore_image(db: AsyncSession, image_id: UUID) -> Image:
    from ..core.exceptions import NotFoundError

    image = await get_image(db, image_id)
    if not image:
        raise NotFoundError(f"Image {image_id} not found")

    image.is_archived = False
    image.archived_at = None
    image.updated_at = datetime.datetime.now(datetime.UTC)
    image.data_update_status = "updated_requires_reindex"
    await db.flush()
    return image


async def mark_bbox_corrected(db: AsyncSession, image_id: UUID) -> Image:
    """Mark an image as having its bounding boxes corrected (e.g. by Data Owner)."""
    from ..core.exceptions import NotFoundError

    image = await get_image(db, image_id)
    if not image:
        raise NotFoundError(f"Image {image_id} not found")

    image.data_update_status = "updated_requires_reindex"
    image.updated_at = datetime.datetime.now(datetime.UTC)
    await db.flush()
    await system_state.increment_counter(db, "bbox_corrections")
    return image
