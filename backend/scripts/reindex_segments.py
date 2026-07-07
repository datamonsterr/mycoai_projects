#!/usr/bin/env python3
"""
Reindex existing segments that lack Qdrant point IDs.

For all segments in the database where qdrant_point_id IS NULL,
extract features from the crop image (MinIO or local) and upsert to Qdrant.

Usage:
    docker compose exec backend uv run python scripts/reindex_segments.py
    docker compose exec backend uv run python scripts/reindex_segments.py --limit 10
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, ".")

logger = logging.getLogger("reindex")


async def main(limit: int = 0) -> dict:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.config import get_settings, get_storage_settings
    from backend.database import _get_sessionmaker
    session_factory = _get_sessionmaker()

    from backend.models import Image, Segment, Species, Strain, Media
    from backend.services.feature_extraction import index_segment_to_qdrant
    from backend.services.storage import create_storage

    settings = get_settings()
    storage = create_storage(get_storage_settings())

    stats = {"total": 0, "indexed": 0, "skipped": 0, "failed": 0, "already_done": 0}

    async with session_factory() as db:
        # Find segments without qdrant_point_id
        stmt = (
            select(Segment)
            .where(Segment.qdrant_point_id.is_(None))
            .where(Segment.is_archived.is_(False))
            .limit(limit if limit > 0 else None)
        )
        result = await db.execute(stmt)
        segments = result.scalars().all()
        stats["total"] = len(segments)
        logger.info("Found %d unindexed segments", stats["total"])

        for i, seg in enumerate(segments):
            logger.info("[%d/%d] Indexing segment %s", i + 1, stats["total"], seg.id)

            # Load related image with strain/species/media
            img_result = await db.execute(
                select(Image)
                .options(
                    selectinload(Image.strain),
                    selectinload(Image.species),
                    selectinload(Image.media),
                )
                .where(Image.id == seg.image_id)
            )
            img = img_result.scalar_one_or_none()
            if not img:
                stats["skipped"] += 1
                logger.warning("  SKIP: image not found for segment")
                continue

            strain_name = img.strain.name if img.strain else "unknown"
            species_name = img.species.name if img.species else "unknown"
            media_name = img.media.name if img.media else "unknown"

            try:
                if seg.crop_path.startswith("/app/Dataset/uploads/"):
                    seg.crop_path = str(settings.upload_root / seg.crop_path.removeprefix("/app/Dataset/uploads/"))
                result = await index_segment_to_qdrant(
                    db,
                    seg,
                    img,
                    strain_name=strain_name,
                    species_name=species_name,
                    media_name=media_name,
                    storage=storage,
                )
                if "error" in result:
                    stats["failed"] += 1
                    logger.warning("  FAIL: %s", result["error"])
                else:
                    stats["indexed"] += 1
                    logger.info("  OK: index=%s", result.get("qdrant_point_id"))
            except Exception as exc:
                stats["failed"] += 1
                logger.error("  FAIL: %s", exc)

            if (i + 1) % 10 == 0:
                await db.commit()

        await db.commit()

    logger.info("Reindex complete: %s", stats)
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Reindex segments to Qdrant")
    parser.add_argument("--limit", type=int, default=0, help="Max segments to index")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    stats = asyncio.run(main(limit=args.limit))
    print(f"\nDone: {stats}")
