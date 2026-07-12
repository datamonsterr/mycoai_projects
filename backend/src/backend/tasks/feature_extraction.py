"""Feature extraction + Qdrant indexing task for a single image segment."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import QdrantIndexState, Segment
from ..services.feature_extraction import extract_features
from ..services.qdrant_client import QdrantClientService

logger = logging.getLogger("feature-extraction-task")


async def run(
    segment_id: UUID,
    db: AsyncSession,
    *,
    collection_name: str = "qdrant-research_fold1",
) -> dict:
    """Extract features from a segment crop and index it in Qdrant.

    Args:
        segment_id: UUID of the segment to index.
        db: Async SQLAlchemy session.
        collection_name: Qdrant collection name.

    Returns:
        Dict with result summary.
    """
    logger.info("Extracting features for segment %s", segment_id)

    result = await db.execute(select(Segment).where(Segment.id == segment_id))
    seg = result.scalar_one_or_none()
    if not seg:
        return {"error": f"Segment {segment_id} not found"}

    crop_path = Path(seg.crop_path)
    if not crop_path.exists():
        return {"error": f"Crop file not found: {seg.crop_path}"}

    # Extract feature vectors
    vectors = extract_features(crop_path)
    if not vectors:
        return {"error": "Feature extraction returned empty vectors"}

    # Upsert to Qdrant
    qdrant_svc = QdrantClientService()
    import uuid as _uuid

    point_id = _uuid.uuid4().int & ((1 << 63) - 1)
    await qdrant_svc.upsert_point(
        point_id=point_id,
        vectors=vectors,
        payload={
            "segment_id": str(seg.id),
            "image_id": str(seg.image_id),
            "segment_index": seg.segment_index,
            "bbox": {
                "x": seg.bbox_x,
                "y": seg.bbox_y,
                "w": seg.bbox_w,
                "h": seg.bbox_h,
            },
        },
    )

    # Record index state
    seg.qdrant_point_id = UUID(int=point_id)
    qis = QdrantIndexState(
        segment_id=seg.id,
        qdrant_point_id=seg.qdrant_point_id,
        collection_name=collection_name,
        is_active=True,
    )
    db.add(qis)
    await db.flush()

    out = {
        "segment_id": str(segment_id),
        "status": "indexed",
        "qdrant_point_id": str(seg.qdrant_point_id),
        "feature_types": list(vectors.keys()),
    }
    logger.info("Feature extraction complete: %s", out)
    return out
