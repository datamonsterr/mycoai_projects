#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")


def discover_original_prepared_images(root: Path) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(root.glob("*/*/*/*/*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            continue
        if path.parent.name.startswith("segments_"):
            continue
        if path.name.startswith(
            ("segment_", "prepared", "pipeline_", "bbox_", "source")
        ):
            continue
        parts = path.relative_to(root).parts
        if len(parts) < 5:
            continue
        species, strain, media, angle = parts[:4]
        items.append(
            {
                "path": str(path),
                "species": species.replace("-", " ").title(),
                "strain": strain.upper().replace("-", " "),
                "media": media.upper(),
                "angle": angle,
            }
        )
    return items


async def _run(root: Path, limit: int) -> dict[str, int]:
    from backend.config import get_settings, get_storage_settings
    from backend.database import _get_sessionmaker
    from backend.routes import _create_image
    from backend.segmentation import SegmentationPipeline
    from backend.services.feature_extraction import index_segment_to_qdrant
    from backend.services.storage import create_storage
    from backend.tasks.batch import _ensure_media, _ensure_species, _ensure_strain

    storage = create_storage(get_storage_settings())
    pipeline = SegmentationPipeline(get_settings().upload_root, storage=storage)
    session_factory = _get_sessionmaker()
    items = discover_original_prepared_images(root)
    if limit > 0:
        items = items[:limit]
    stats = {"images": 0, "segments": 0, "indexed": 0}

    async with session_factory() as db:
        for item in items:
            record = await asyncio.to_thread(
                pipeline.segment_upload,
                Path(item["path"]),
                strain=item["strain"],
                media=item["media"],
                method="yolo",
            )
            species_obj = await _ensure_species(db, item["species"])
            media_obj = await _ensure_media(db, item["media"])
            strain_obj = await _ensure_strain(db, item["strain"], species_obj.id)
            image_obj = await _create_image(
                db,
                record,
                strain_obj,
                species_obj,
                media_obj,
                commit=False,
            )
            image_obj.angle = item["angle"] or None
            await db.flush()
            stats["images"] += 1
            stats["segments"] += len(image_obj.segments)
            for segment in image_obj.segments:
                result = await index_segment_to_qdrant(
                    db,
                    segment,
                    image_obj,
                    strain_name=strain_obj.name,
                    species_name=species_obj.name,
                    media_name=media_obj.name,
                    storage=storage,
                    collection_name="myco_fungi_features_full_finetuned",
                )
                if "error" not in result:
                    stats["indexed"] += 1
            await db.commit()
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run YOLO + EffB1 pipeline from Dataset/original_prepared"
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path("../Dataset/original_prepared"),
    )
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    stats = asyncio.run(_run(args.dataset_root, args.limit))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
