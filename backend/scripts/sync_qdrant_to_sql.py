#!/usr/bin/env python3
"""
Sync Qdrant research data → Backend SQL database (PostgreSQL).

Reads all points from the Qdrant collection, extracts unique species, media,
and strain entries, then seeds the backend SQL database via the import_dto
data path.

Usage:
    uv run python scripts/sync_qdrant_to_sql.py
    uv run python scripts/sync_qdrant_to_sql.py --collection myco_fungi_features_full_finetuned
    uv run python scripts/sync_qdrant_to_sql.py --scan-only   # dry run

Requires: backend + Qdrant running
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import defaultdict
from typing import Any

sys.path.insert(0, ".")

logger = logging.getLogger("qdrant-sync")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


async def scan_qdrant(collection: str) -> dict[str, Any]:
    """Scroll through all Qdrant points and extract unique entities."""
    from qdrant_client import QdrantClient

    client = QdrantClient(host="localhost", port=6333)

    try:
        info = client.get_collection(collection)
        total = info.points_count or 0
        logger.info("Collection '%s': %d points", collection, total)
    except Exception as exc:
        logger.error("Cannot access Qdrant: %s", exc)
        sys.exit(1)

    species_set: set[str] = set()
    media_set: set[str] = set()
    strains: dict[str, str] = {}  # strain → species
    strain_media_map: defaultdict[str, set[str]] = defaultdict(set)

    offset: int | str | None = None
    scanned = 0
    batch = 0

    while True:
        points, next_offset = client.scroll(
            collection_name=collection,
            limit=500,
            offset=offset,
            with_payload=True,
        )
        if not points:
            break

        offset = next_offset
        batch += 1
        scanned += len(points)

        for point in points:
            payload = point.payload or {}
            strain = payload.get("strain", "")
            specy = payload.get("specy") or payload.get("species", "")
            env = payload.get("environment", "")

            if specy and specy.lower() != "unknown":
                species_set.add(specy)
            if env and env.lower() != "unknown":
                media_set.add(env.upper())
            if strain and specy:
                strains[strain] = specy
            if strain and env:
                strain_media_map[strain].add(env.upper())

        if scanned % 5000 == 0 and scanned > 0:
            logger.info("  Scanned %d points...", scanned)

        if next_offset is None:
            break

    logger.info(
        "Scan complete: %d points, %d species, %d media, %d strains",
        scanned,
        len(species_set),
        len(media_set),
        len(strains),
    )
    return {
        "species": sorted(species_set),
        "media": sorted(media_set),
        "strains": strains,
        "total_points": scanned,
    }


async def sync_to_sql(manifest: dict[str, Any]) -> dict[str, int]:
    """Seed species, media, and strains into the backend SQL database."""
    from backend.database import async_session as session_factory
    from backend.models import Media, Species, Strain

    stats: dict[str, int] = {"species_created": 0, "media_created": 0, "strains_created": 0}

    async with session_factory() as db:
        from sqlalchemy import select

        # Seed species
        for name in manifest["species"]:
            result = await db.execute(select(Species).where(Species.name == name))
            if result.scalar_one_or_none() is None:
                from uuid import uuid4

                db.add(Species(id=uuid4(), name=name, description=None))
                stats["species_created"] += 1
        await db.flush()
        logger.info("  Species: %d new of %d", stats["species_created"], len(manifest["species"]))

        # Seed media
        for name in manifest["media"]:
            result = await db.execute(select(Media).where(Media.name == name))
            if result.scalar_one_or_none() is None:
                from uuid import uuid4

                db.add(Media(id=uuid4(), name=name, description=None))
                stats["media_created"] += 1
        await db.flush()
        logger.info("  Media: %d new of %d", stats["media_created"], len(manifest["media"]))

        # Seed strains
        species_cache: dict[str, str] = {}
        for strain_name, specy_name in manifest["strains"].items():
            if specy_name not in species_cache:
                result = await db.execute(
                    select(Species.id).where(Species.name == specy_name)
                )
                row = result.scalar_one_or_none()
                if row is None:
                    continue
                species_cache[specy_name] = str(row)

            existing = await db.execute(
                select(Strain).where(
                    Strain.name == strain_name,
                    Strain.species_id == species_cache[specy_name],
                )
            )
            if existing.scalar_one_or_none() is None:
                from uuid import uuid4

                db.add(
                    Strain(
                        id=uuid4(),
                        name=strain_name,
                        species_id=species_cache[specy_name],
                        source="qdrant_import",
                    )
                )
                stats["strains_created"] += 1

        await db.commit()
        logger.info("  Strains: %d new of %d", stats["strains_created"], len(manifest["strains"]))

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Qdrant → SQL")
    parser.add_argument(
        "--collection",
        default="myco_fungi_features_full_finetuned",
        help="Qdrant collection name",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan and report, do not sync to SQL",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        default=True,
        help="Sync to SQL (default)",
    )
    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    manifest = asyncio.run(scan_qdrant(args.collection))

    print("\n=== Qdrant Scan Summary ===")
    print(f"  Total points: {manifest['total_points']}")
    print(f"  Species: {len(manifest['species'])}")
    for s in manifest["species"][:10]:
        print(f"    - {s}")
    if len(manifest["species"]) > 10:
        print(f"    ... and {len(manifest['species']) - 10} more")

    print(f"  Media: {len(manifest['media'])}")
    for m in manifest["media"]:
        print(f"    - {m}")

    print(f"  Strains: {len(manifest['strains'])}")
    for i, (strain, specy) in enumerate(manifest["strains"].items()):
        if i >= 10:
            print(f"    ... and {len(manifest['strains']) - 10} more")
            break
        print(f"    - {strain} → {specy}")

    if args.scan_only:
        return

    print("\n=== Syncing to SQL ===")
    try:
        stats = asyncio.run(sync_to_sql(manifest))
        print("Sync complete:", stats)
    except Exception as exc:
        logger.error("Sync failed: %s", exc)
        print("\nMake sure the backend database is running and accessible.")
        print("  docker compose up -d postgres")
        sys.exit(1)


if __name__ == "__main__":
    main()
