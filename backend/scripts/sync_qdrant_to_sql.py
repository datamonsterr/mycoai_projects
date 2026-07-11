#!/usr/bin/env python3
"""
Sync Qdrant research data → Backend SQL database (PostgreSQL).

Reads all points from the Qdrant collection, extracts unique species, media,
and strain entries, then seeds the backend SQL database via the import_dto
data path.

Usage:
    uv run python scripts/sync_qdrant_to_sql.py
    uv run python scripts/sync_qdrant_to_sql.py --collection qdrant-research_fold0
    uv run python scripts/sync_qdrant_to_sql.py \
        --collection myco_fungi_features_full_finetuned
    uv run python scripts/sync_qdrant_to_sql.py --scan-only   # dry run

Requires: backend + Qdrant running
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

sys.path.insert(0, ".")

logger = logging.getLogger("qdrant-sync")


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


DATASET_MEDIA_RE = {
    "CREA",
    "CYA30",
    "CYAS",
    "CYA",
    "DG18",
    "MEA",
    "YES",
    "OA",
    "M40Y",
}


def scan_original_prepared_media(root: Path) -> set[str]:
    media: set[str] = set()
    if not root.exists():
        return media
    for species_dir in root.iterdir():
        if not species_dir.is_dir():
            continue
        for strain_dir in species_dir.iterdir():
            if not strain_dir.is_dir():
                continue
            for media_dir in strain_dir.iterdir():
                if not media_dir.is_dir():
                    continue
                name = media_dir.name.upper()
                if name in DATASET_MEDIA_RE:
                    media.add("CYA" if name in {"CYA30", "CYAS"} else name)
    return media


async def _load_sql_segment_metadata() -> tuple[
    dict[str, dict[str, str]],
    dict[tuple[str, str, str, str, str], dict[str, str]],
]:
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from backend.database import _get_sessionmaker
    from backend.models import Image, Segment

    async with _get_sessionmaker()() as db:
        result = await db.execute(
            select(Segment)
            .join(Image, Segment.image_id == Image.id)
            .options(
                selectinload(Segment.image).selectinload(Image.media),
                selectinload(Segment.image).selectinload(Image.species),
                selectinload(Segment.image).selectinload(Image.strain),
            )
            .where(Segment.is_archived.is_(False), Image.is_archived.is_(False))
        )
        segments = result.scalars().all()

    by_segment_id: dict[str, dict[str, str]] = {}
    by_legacy_key: dict[tuple[str, str, str, str, str], dict[str, str]] = {}
    for segment in segments:
        image = segment.image
        if (
            image is None
            or image.media is None
            or image.species is None
            or image.strain is None
        ):
            continue
        entry = {
            "segment_id": str(segment.id),
            "image_id": str(image.id),
            "parent_id": str(image.id),
            "parent_item_id": str(image.id),
            "parent_image_id": str(image.id),
            "strain": image.strain.name,
            "species": image.species.name,
            "specy": image.species.name,
            "media": image.media.name,
            "environment": image.media.name,
            "angle": image.angle or "",
            "segment_index": str(segment.segment_index),
        }
        by_segment_id[str(segment.id)] = entry
        by_legacy_key[
            (
                image.strain.name.casefold(),
                image.media.name.casefold(),
                (image.angle or "").casefold(),
                str(segment.segment_index),
                Path(segment.crop_path).name,
            )
        ] = entry
    return by_segment_id, by_legacy_key


def _lookup_sql_meta(
    payload: dict[str, Any],
    sql_segment_metadata: dict[str, dict[str, str]],
    sql_legacy_metadata: dict[tuple[str, str, str, str, str], dict[str, str]],
) -> dict[str, str] | None:
    segment_id = str(payload.get("segment_id") or "")
    if segment_id:
        sql_meta = sql_segment_metadata.get(segment_id)
        if sql_meta is not None:
            return sql_meta
    segment_path = str(payload.get("segment_path") or "")
    if not segment_path:
        return None
    segment_index = payload.get("segment_index")
    return sql_legacy_metadata.get(
        (
            str(payload.get("strain") or "").casefold(),
            str(payload.get("media") or payload.get("environment") or "").casefold(),
            str(payload.get("angle") or "").casefold(),
            "" if segment_index is None else str(segment_index),
            Path(segment_path).name,
        )
    )


def _copy_collection_vectors(
    source_collection: str,
    target_collection: str,
    sql_segment_metadata: dict[str, dict[str, str]],
    sql_legacy_metadata: dict[tuple[str, str, str, str, str], dict[str, str]],
    *,
    source_host: str = "localhost",
    source_port: int = 6333,
    target_host: str = "localhost",
    target_port: int = 6335,
) -> dict[str, int]:
    source = QdrantClient(host=source_host, port=source_port)
    target = QdrantClient(host=target_host, port=target_port)

    source_info = source.get_collection(source_collection)
    target.recreate_collection(
        collection_name=target_collection,
        vectors_config=source_info.config.params.vectors,
    )

    copied = 0
    skipped_missing_sql = 0
    offset: int | str | None = None
    while True:
        points, next_offset = source.scroll(
            collection_name=source_collection,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )
        if not points:
            break

        upserts: list[PointStruct] = []
        for point in points:
            payload = point.payload or {}
            sql_meta = _lookup_sql_meta(
                payload,
                sql_segment_metadata,
                sql_legacy_metadata,
            )
            if sql_meta is None:
                skipped_missing_sql += 1
                continue
            merged_payload = {**payload, **sql_meta}
            upserts.append(
                PointStruct(
                    id=point.id,
                    vector=point.vector,
                    payload=merged_payload,
                )
            )

        if upserts:
            target.upsert(collection_name=target_collection, points=upserts)
            copied += len(upserts)
        offset = next_offset
        if next_offset is None:
            break

    target_info = target.get_collection(target_collection)
    target_points = target_info.points_count or 0
    return {
        "vectors_copied": copied,
        "skipped_missing_sql": skipped_missing_sql,
        "target_points": int(target_points),
        "sql_segments": len(sql_segment_metadata),
    }


async def scan_qdrant(collection: str) -> dict[str, Any]:
    """Scroll through all Qdrant points and extract unique entities."""
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
            env = payload.get("media", "")

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

    dataset_media = scan_original_prepared_media(Path("Dataset/original_prepared"))
    media_set.update(dataset_media)

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
    from backend.database import _get_sessionmaker
    from backend.models import Media, Species, Strain

    stats: dict[str, int] = {
        "species_created": 0,
        "media_created": 0,
        "strains_created": 0,
    }

    async with _get_sessionmaker()() as db:
        from sqlalchemy import select

        # Seed species
        for name in manifest["species"]:
            result = await db.execute(select(Species).where(Species.name == name))
            if result.scalar_one_or_none() is None:
                from uuid import uuid4

                db.add(Species(id=uuid4(), name=name, description=None))
                stats["species_created"] += 1
        await db.flush()
        logger.info(
            "  Species: %d new of %d",
            stats["species_created"],
            len(manifest["species"]),
        )

        # Seed media
        for name in manifest["media"]:
            result = await db.execute(select(Media).where(Media.name == name))
            if result.scalar_one_or_none() is None:
                from uuid import uuid4

                db.add(Media(id=uuid4(), name=name, description=None))
                stats["media_created"] += 1
        await db.flush()
        logger.info(
            "  Media: %d new of %d", stats["media_created"], len(manifest["media"])
        )

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
        logger.info(
            "  Strains: %d new of %d",
            stats["strains_created"],
            len(manifest["strains"]),
        )

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync research Qdrant → SQL + product Qdrant"
    )
    parser.add_argument(
        "--collection",
        default="qdrant-research_fold0",
        help="Qdrant collection name",
    )
    parser.add_argument(
        "--scan-only",
        action="store_true",
        help="Only scan and report, do not sync to SQL or product Qdrant",
    )
    parser.add_argument(
        "--target-collection",
        default="myco_fungi_features_full_finetuned",
        help="Product Qdrant collection name",
    )
    parser.add_argument(
        "--verbose",
        "-v",
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
        sql_stats = asyncio.run(sync_to_sql(manifest))
        sql_segment_metadata, sql_legacy_metadata = asyncio.run(
            _load_sql_segment_metadata()
        )
        vector_stats = _copy_collection_vectors(
            args.collection,
            args.target_collection,
            sql_segment_metadata,
            sql_legacy_metadata,
        )
        if vector_stats["vectors_copied"] != vector_stats["target_points"]:
            raise RuntimeError("Qdrant product point count mismatch after sync")
        if vector_stats["target_points"] != vector_stats["sql_segments"]:
            raise RuntimeError("Qdrant product / SQL segment count mismatch after sync")
        print("SQL sync complete:", sql_stats)
        print("Qdrant product sync complete:", vector_stats)
    except Exception as exc:
        logger.error("Sync failed: %s", exc)
        print("\nMake sure Postgres + both Qdrant instances are running.")
        print("  docker compose up -d postgres qdrant-research qdrant-product")
        sys.exit(1)


if __name__ == "__main__":
    main()
