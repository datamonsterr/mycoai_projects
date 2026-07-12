#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, ".")


@dataclass
class ImportStats:
    rows: int = 0
    would_upsert_species: int = 0
    would_upsert_strains: int = 0
    would_upsert_media: int = 0
    would_upsert_segments: int = 0
    imported_segments: int = 0
    imported_images: int = 0
    missing_segment_objects: list[str] | None = None
    extractor_counts: dict[str, int] | None = None
    dry_run: bool = False


@dataclass
class SegmentRow:
    row_id: str
    segment_path: Path
    species: str
    strain: str
    media: str
    angle: str
    segment_index: int
    segmentation_method: str


def _extract_row_fields(
    row: dict[str, Any],
) -> tuple[str, str, str, str, str, int, str]:
    info = row.get("metadata", {}).get("instance_info", {})
    segmentation = row.get("metadata", {}).get("segmentation", {})
    return (
        str(info.get("species") or "unknown-species"),
        str(info.get("strain") or "unknown-strain"),
        str(info.get("environment") or "unknown-media"),
        str(info.get("angle") or ""),
        str(row.get("segment_path") or ""),
        int(row.get("metadata", {}).get("index") or 0),
        str(segmentation.get("method") or "yolo"),
    )


def _resolve_segment_path(features_path: Path, segment_path: str) -> Path:
    path = Path(segment_path)
    if path.is_absolute() and path.exists():
        return path
    candidates = [
        path,
        features_path.parent / path,
        Path.cwd() / path,
        Path.cwd().parent / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return path


def _load_rows(
    features_path: Path,
) -> tuple[list[SegmentRow], dict[str, int], list[str]]:
    raw_rows = json.loads(features_path.read_text())
    rows: list[SegmentRow] = []
    extractor_counts: dict[str, int] = {}
    missing_segment_objects: list[str] = []
    for raw in raw_rows:
        species, strain, media, angle, segment_path, segment_index, method = (
            _extract_row_fields(raw)
        )
        path = _resolve_segment_path(features_path, segment_path)
        if segment_path and not path.exists():
            missing_segment_objects.append(segment_path)
        for extractor_name in raw.get("features", {}):
            extractor_counts[extractor_name] = (
                extractor_counts.get(extractor_name, 0) + 1
            )
        rows.append(
            SegmentRow(
                row_id=str(raw.get("id") or f"{strain}-{segment_index}"),
                segment_path=path,
                species=species,
                strain=strain,
                media=media,
                angle=angle,
                segment_index=segment_index,
                segmentation_method=method,
            )
        )
    return rows, extractor_counts, missing_segment_objects


async def _run_import(features_path: Path, dry_run: bool) -> dict[str, Any]:
    from backend.config import get_qdrant_settings, get_storage_settings
    from backend.database import _get_sessionmaker
    from backend.routes import _create_image
    from backend.services.feature_extraction import index_segment_to_qdrant
    from backend.services.storage import create_storage, storage_artifact_prefix
    from backend.tasks.batch import _ensure_media, _ensure_species, _ensure_strain

    rows, extractor_counts, missing_segment_objects = _load_rows(features_path)
    species_names = {row.species for row in rows}
    strain_names = {(row.species, row.strain) for row in rows}
    media_names = {row.media for row in rows}
    stats = ImportStats(
        rows=len(rows),
        would_upsert_species=len(species_names),
        would_upsert_strains=len(strain_names),
        would_upsert_media=len(media_names),
        would_upsert_segments=len(rows),
        missing_segment_objects=missing_segment_objects,
        extractor_counts=extractor_counts,
        dry_run=dry_run,
    )
    if dry_run:
        return stats.__dict__

    storage = create_storage(get_storage_settings())
    session_factory = _get_sessionmaker()
    collection_name = "myco_fungi_features_full_finetuned"
    qdrant_settings = get_qdrant_settings()
    original_collection = qdrant_settings.collection_name
    qdrant_settings.collection_name = collection_name

    grouped: dict[tuple[str, str, str, str], list[SegmentRow]] = defaultdict(list)
    for row in rows:
        grouped[(row.species, row.strain, row.media, row.angle)].append(row)

    try:
        async with session_factory() as db:
            for (
                species_name,
                strain_name,
                media_name,
                angle,
            ), image_rows in grouped.items():
                species_obj = await _ensure_species(db, species_name)
                media_obj = await _ensure_media(db, media_name)
                strain_obj = await _ensure_strain(db, strain_name, species_obj.id)
                image_id = str(uuid.uuid4())
                artifact_dir = storage_artifact_prefix(
                    strain=strain_name,
                    media=media_name,
                    image_id=image_id,
                )
                source_key = artifact_dir / "source.jpg"
                prepared_key = artifact_dir / "prepared.jpg"
                pipeline_key = (
                    artifact_dir / f"pipeline_{image_rows[0].segmentation_method}.jpg"
                )
                placeholder = b"placeholder"
                storage.upload_bytes(str(source_key), placeholder)
                storage.upload_bytes(str(prepared_key), placeholder)
                storage.upload_bytes(str(pipeline_key), placeholder)
                record = SimpleNamespace(
                    image_id=image_id,
                    source_path=source_key,
                    artifact_dir=artifact_dir,
                    segmentation_method=image_rows[0].segmentation_method,
                    segments=[],
                )
                for row in sorted(image_rows, key=lambda item: item.segment_index):
                    crop_bytes = (
                        row.segment_path.read_bytes()
                        if row.segment_path.exists()
                        else placeholder
                    )
                    crop_key = (
                        artifact_dir / "segments" / f"segment_{row.segment_index}.jpg"
                    )
                    storage.upload_bytes(str(crop_key), crop_bytes)
                    record.segments.append(
                        SimpleNamespace(
                            segment_index=row.segment_index,
                            bbox=SimpleNamespace(x=0, y=0, w=0, h=0),
                        )
                    )
                image_obj = await _create_image(
                    db,
                    record,
                    strain_obj,
                    species_obj,
                    media_obj,
                    commit=False,
                )
                image_obj.angle = angle or None
                await db.flush()
                stats.imported_images += 1
                for segment in image_obj.segments:
                    result = await index_segment_to_qdrant(
                        db,
                        segment,
                        image_obj,
                        strain_name=strain_name,
                        species_name=species_name,
                        media_name=media_name,
                        storage=storage,
                        collection_name=(collection_name),
                    )
                    if "error" not in result:
                        stats.imported_segments += 1
                await db.commit()
    finally:
        qdrant_settings.collection_name = original_collection

    return stats.__dict__


def run_sync(*, features_path: Path, dry_run: bool = False) -> dict[str, Any]:
    return asyncio.run(_run_import(features_path=features_path, dry_run=dry_run))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync research YOLO features into SQL, storage, qdrant-product"
    )
    parser.add_argument("--features-json", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    report = run_sync(features_path=args.features_json, dry_run=args.dry_run)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
