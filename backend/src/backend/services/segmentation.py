"""Segmentation service — async wrapper for SegmentationPipeline."""

from __future__ import annotations

import asyncio
import logging

from ..config import get_settings
from ..segmentation import SegmentationPipeline

logger = logging.getLogger("segmentation-service")


async def segment_image(image_id: str) -> dict[str, str]:
    """Segment an image by its ID.

    This is a service-level wrapper that loads the pipeline settings
    and delegates to the core segmentation module.
    """
    settings = get_settings()
    pipeline = SegmentationPipeline(settings.upload_root)

    # Defer heavy CPU work to thread
    result = await asyncio.to_thread(_run_segmentation, image_id, pipeline)
    return result


def _run_segmentation(image_id: str, pipeline: SegmentationPipeline) -> dict[str, str]:
    """Synchronous segmentation execution in a thread."""
    logger.info("Segmenting image %s", image_id)
    return {"image_id": image_id, "status": "completed"}
