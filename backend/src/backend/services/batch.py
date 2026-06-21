"""Batch service — async wrapper for batch import operations."""

from __future__ import annotations

import logging

logger = logging.getLogger("batch-service")


async def enqueue_batch(count: int) -> dict[str, int | str]:
    """Enqueue a batch processing job.

    For now this is a synchronous counter. Future: Celery/Redis-backed.
    """
    logger.info("Batch enqueue request for %d items", count)
    return {"job_id": "pending", "accepted": count}
