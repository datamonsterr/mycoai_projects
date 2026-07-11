#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from minio import Minio
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from backend.config import get_qdrant_settings, get_storage_settings
from backend.database import _get_sessionmaker
from backend.models import Image, Media, QdrantIndexState, Segment, Species, Strain
from backend.services.storage import storage_artifact_prefix, storage_candidates

REPO_ROOT = Path(__file__).resolve().parents[2]


def _slugify(value: str) -> str:
    normalized = "".join(
        ch.lower() if ch.isalnum() else "-" for ch in value
    )
    return "-".join(part for part in normalized.split("-") if part)


def _canonical_species_by_slug() -> dict[str, str]:
    root = REPO_ROOT / "Dataset/original_prepared"
    return {
        path.name: path.name.replace("-", " ").title()
        for path in root.iterdir()
        if path.is_dir()
    }


def _strain_species_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    csv_path = REPO_ROOT / "Dataset/strain_to_specy.csv"
    if not csv_path.exists():
        return mapping
    rows = csv_path.read_text().splitlines()
    for row in rows[1:]:
        parts = [part.strip() for part in row.split(",")]
        if len(parts) >= 2 and parts[0] and parts[1]:
            mapping[parts[0].casefold()] = parts[1]
    return mapping


def _upload_root() -> Path:
    root = Path(get_storage_settings().upload_root)
    if not root.is_absolute():
        root = (REPO_ROOT / "backend" / root).resolve()
    return root


def _minio() -> Minio:
    settings = get_storage_settings()
    return Minio(
        endpoint=settings.s3_endpoint.replace("http://", "").replace("https://", ""),
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=settings.s3_secure,
    )


def _bucket() -> str:
    return get_storage_settings().s3_bucket


def _object_exists(client: Minio, key: str) -> bool:
    try:
        client.stat_object(_bucket(), key)
        return True
    except Exception:
        return False


async def normalize_storage_paths() -> dict[str, int]:
    session_factory = _get_sessionmaker()
    stats = Counter()
    async with session_factory() as db:
        result = await db.execute(
            select(Image).options(
                selectinload(Image.strain),
                selectinload(Image.media),
                selectinload(Image.segments),
            )
        )
        images = result.scalars().all()
        for img in images:
            if img.strain is None or img.media is None:
                continue
            prefix = storage_artifact_prefix(
                strain=img.strain.name,
                media=img.media.name,
                image_id=img.id,
            )
            source = str(prefix / "source.jpg")
            prepared = str(prefix / "prepared.jpg")
            pipeline = str(prefix / "pipeline_kmeans.jpg")
            if img.file_path != source:
                img.file_path = source
                stats["images_updated"] += 1
            if img.prepared_path != prepared:
                img.prepared_path = prepared
                stats["prepared_updated"] += 1
            if img.pipeline_path != pipeline:
                img.pipeline_path = pipeline
                stats["pipeline_updated"] += 1
            for seg in img.segments:
                crop = str(prefix / "segments" / f"segment_{seg.segment_index}.jpg")
                if seg.crop_path != crop:
                    seg.crop_path = crop
                    stats["segments_updated"] += 1
        await db.commit()
    return dict(stats)


async def normalize_species() -> dict[str, int]:
    session_factory = _get_sessionmaker()
    stats = Counter()
    canonical_by_slug = _canonical_species_by_slug()
    strain_map = _strain_species_map()

    async with session_factory() as db:
        species_rows = list((await db.execute(select(Species))).scalars())
        species_by_name = {sp.name: sp for sp in species_rows}
        canonical_species: dict[str, Species] = {}
        for canonical_name in canonical_by_slug.values():
            species = species_by_name.get(canonical_name)
            if species is None:
                species = Species(name=canonical_name, description=None)
                db.add(species)
                await db.flush()
                stats["species_created"] += 1
            canonical_species[canonical_name] = species

        strains = list(
            (
                await db.execute(
                    select(Strain).options(
                        selectinload(Strain.species),
                        selectinload(Strain.images),
                    )
                )
            ).scalars()
        )
        for strain in strains:
            target_name = strain_map.get(strain.name.casefold())
            if target_name is None:
                current = strain.species.name if strain.species else ""
                target_name = canonical_by_slug.get(_slugify(current), current)
            if not target_name:
                continue
            target_species = canonical_species.get(target_name)
            if target_species is None:
                continue
            if strain.species_id != target_species.id:
                strain.species_id = target_species.id
                stats["strains_reassigned"] += 1
            for image in strain.images:
                if image.species_id != target_species.id:
                    image.species_id = target_species.id
                    stats["images_reassigned"] += 1

        await db.commit()
    return dict(stats)


async def prune_orphans() -> dict[str, int]:
    session_factory = _get_sessionmaker()
    stats = Counter()
    async with session_factory() as db:
        strain_ids = list(
            (
                await db.execute(
                    select(Strain.id)
                    .outerjoin(Image, Image.strain_id == Strain.id)
                    .group_by(Strain.id)
                    .having(func.count(Image.id) == 0)
                )
            ).scalars()
        )
        if strain_ids:
            await db.execute(delete(Strain).where(Strain.id.in_(strain_ids)))
            stats["strains_deleted"] = len(strain_ids)

        species_ids = list(
            (
                await db.execute(
                    select(Species.id)
                    .outerjoin(Image, Image.species_id == Species.id)
                    .group_by(Species.id)
                    .having(func.count(Image.id) == 0)
                )
            ).scalars()
        )
        if species_ids:
            await db.execute(delete(Species).where(Species.id.in_(species_ids)))
            stats["species_deleted"] = len(species_ids)

        media_ids = list(
            (
                await db.execute(
                    select(Media.id)
                    .outerjoin(Image, Image.media_id == Media.id)
                    .group_by(Media.id)
                    .having(func.count(Image.id) == 0)
                )
            ).scalars()
        )
        if media_ids:
            await db.execute(delete(Media).where(Media.id.in_(media_ids)))
            stats["media_deleted"] = len(media_ids)

        await db.commit()
    return dict(stats)


async def audit() -> dict[str, object]:
    session_factory = _get_sessionmaker()
    client = _minio()
    upload_root = _upload_root()
    qdrant = get_qdrant_settings()
    out: dict[str, object] = {}

    async with session_factory() as db:
        images = list(
            (
                await db.execute(
                    select(Image).options(
                        selectinload(Image.strain),
                        selectinload(Image.media),
                        selectinload(Image.species),
                        selectinload(Image.segments),
                    )
                )
            ).scalars()
        )
        species_distribution = [
            {"name": name, "image_count": image_count}
            for name, image_count in (
                await db.execute(
                    select(Species.name, func.count(Image.id))
                    .outerjoin(Image, Image.species_id == Species.id)
                    .group_by(Species.name)
                    .order_by(func.count(Image.id).desc(), Species.name)
                )
            ).all()
        ]
        out["sql"] = {
            "species": (
                await db.execute(select(func.count()).select_from(Species))
            ).scalar()
            or 0,
            "media": (
                await db.execute(select(func.count()).select_from(Media))
            ).scalar()
            or 0,
            "strains": (
                await db.execute(select(func.count()).select_from(Strain))
            ).scalar()
            or 0,
            "images": len(images),
            "segments": sum(len(img.segments) for img in images),
            "qdrant_index_states": (
                await db.execute(select(func.count()).select_from(QdrantIndexState))
            ).scalar()
            or 0,
            "species_distribution": species_distribution,
            "canonical_species": sorted(_canonical_species_by_slug().values()),
        }

    counts = Counter()
    missing: list[dict[str, str | int]] = []
    for img in images:
        prefix = storage_artifact_prefix(
            strain=img.strain.name if img.strain else "unknown",
            media=img.media.name if img.media else "unknown",
            image_id=img.id,
        )
        expected = [
            (Path(img.file_path), "source"),
            (Path(img.prepared_path or prefix / "prepared.jpg"), "prepared"),
            (
                Path(img.pipeline_path or prefix / "pipeline_kmeans.jpg"),
                "pipeline_kmeans",
            ),
        ]
        for seg in img.segments:
            expected.append((Path(seg.crop_path), "segment"))
        for path, kind in expected:
            counts[f"expected_{kind}"] += 1
            ok = False
            for key in storage_candidates(
                path,
                upload_root=upload_root,
                strain=img.strain.name if img.strain else None,
                media=img.media.name if img.media else None,
                image_id=img.id,
            ):
                if _object_exists(client, key):
                    ok = True
                    break
            if ok:
                counts[f"present_{kind}"] += 1
            else:
                counts[f"missing_{kind}"] += 1
                if len(missing) < 20:
                    missing.append(
                        {"image_id": str(img.id), "kind": kind, "path": str(path)}
                    )

    object_count = sum(1 for _ in client.list_objects(_bucket(), recursive=True))
    out["minio"] = {**dict(counts), "objects": object_count, "sample_missing": missing}
    out["qdrant"] = {
        "research_collection": qdrant.collection_name,
    }
    return out


async def clear_runtime() -> dict[str, int]:
    from qdrant_client import QdrantClient

    session_factory = _get_sessionmaker()
    stats = Counter()
    async with session_factory() as db:
        await db.execute(delete(QdrantIndexState))
        await db.execute(delete(Segment))
        await db.execute(delete(Image))
        await db.execute(delete(Strain))
        await db.execute(delete(Species))
        await db.execute(delete(Media))
        await db.commit()
        stats["sql_cleared"] = 1

    client = _minio()
    objects = list(client.list_objects(_bucket(), recursive=True))
    for obj in objects:
        client.remove_object(_bucket(), obj.object_name)
    stats["minio_objects_deleted"] = len(objects)

    qdrant = QdrantClient(host="localhost", port=6335)
    collection = "myco_fungi_features_full_finetuned"
    if collection in {c.name for c in qdrant.get_collections().collections}:
        qdrant.delete_collection(collection)
        stats["qdrant_product_deleted"] = 1
    return dict(stats)


async def _main(args: argparse.Namespace) -> None:
    result: dict[str, object] = {}
    if args.command == "normalize-storage-paths":
        result = await normalize_storage_paths()
    elif args.command == "normalize-species":
        result = await normalize_species()
    elif args.command == "prune-orphans":
        result = await prune_orphans()
    elif args.command == "audit":
        result = await audit()
    elif args.command == "clear-runtime":
        result = await clear_runtime()
    print(json.dumps(result, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset/audit backend runtime state")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("normalize-storage-paths")
    sub.add_parser("normalize-species")
    sub.add_parser("prune-orphans")
    sub.add_parser("audit")
    sub.add_parser("clear-runtime")
    args = parser.parse_args()
    asyncio.run(_main(args))


if __name__ == "__main__":
    main()
