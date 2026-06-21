"""Segmentation task — re-runs segmentation on an existing image.

Reads source image from file_path, re-runs kmeans/contour segmentation,
updates DB segment records, and returns result.
"""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Image, Segment
from ..segmentation import SegmentationPipeline

logger = logging.getLogger("segmentation-task")


async def run(
    image_id: UUID,
    db: AsyncSession,
    pipeline: SegmentationPipeline,
    *,
    method: str = "kmeans",
) -> dict:
    """Re-segment an image and update its DB records.

    Args:
        image_id: UUID of the image to re-segment.
        db: Async SQLAlchemy session.
        pipeline: SegmentationPipeline instance.
        method: Segmentation method ('kmeans' or 'contour').

    Returns:
        Dict with result summary.
    """
    logger.info("Re-segmenting image %s with method=%s", image_id, method)

    # Load image from DB
    result = await db.execute(
        select(Image)
        .options(selectinload(Image.segments).selectinload(Segment.qdrant_index_state))
        .where(Image.id == image_id)
    )
    img = result.scalar_one_or_none()
    if not img:
        return {"error": f"Image {image_id} not found"}

    source_path = Path(img.file_path)
    if not source_path.exists():
        return {"error": f"Source file not found: {img.file_path}"}

    # Load strain/media for artifact path
    strain = img.strain
    strain_name = strain.name if strain else "unknown"

    media_name = "unknown"
    if img.media_id:
        from ..models import Media

        media_result = await db.execute(select(Media).where(Media.id == img.media_id))
        media = media_result.scalar_one_or_none()
        media_name = media.name if media else "unknown"

    # Run segmentation
    record = pipeline.segment_upload(
        source_path,
        strain=strain_name,
        media=media_name,
        method=method,
    )

    # Delete old segments
    for seg in img.segments:
        seg.is_archived = True
    await db.flush()

    # Create new segments
    new_count = 0
    for seg_model in record.segments:
        segment = Segment(
            image_id=img.id,
            segment_index=seg_model.segment_index,
            crop_path=str(
                record.artifact_dir
                / "segments"
                / f"segment_{seg_model.segment_index}.jpg"
            ),
            bbox_x=seg_model.bbox.x,
            bbox_y=seg_model.bbox.y,
            bbox_w=seg_model.bbox.w,
            bbox_h=seg_model.bbox.h,
            segmentation_method=method,
        )
        db.add(segment)
        new_count += 1

    img.data_update_status = "updated_requires_reindex"
    await db.flush()

    out = {
        "image_id": str(image_id),
        "status": "completed",
        "segments_before": len([s for s in img.segments if not s.is_archived]),
        "segments_after": new_count,
        "method": method,
    }
    logger.info("Re-segmentation complete: %s", out)
    return out
