"""Batch import task — imports a directory of fungal images into PostgreSQL + Qdrant.

Pipeline per image:
  1. Parse metadata from filename (species, strain, media, angle)
  2. Segment image via kmeans or contour
  3. Persist Image + Segment records to PostgreSQL
  4. Extract feature vectors for each segment
  5. Upsert vectors to Qdrant and record index state
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Image, Media, QdrantIndexState, Segment, Species, Strain
from ..segmentation import SegmentationPipeline
from ..services.feature_extraction import extract_features
from ..services.qdrant_client import QdrantClientService

logger = logging.getLogger("batch-import")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".jpe"}
SKIP_NAMES = {"thumbs.db", ".ds_store", "desktop.ini"}
DTO_FOLDER_RE_PATTERN = r"^(DTO\s+[\d\-A-Za-z]+)\s+(Penicillium\s+\w+.*)$"
MEDIA_ANGLE_RE_PATTERN = r"(CREA|CYA30|CYAS|CYA|DG18|MEA|YES|OA|M40Y)(ob|rev)"


class BatchImportResult:
    def __init__(self) -> None:
        self.total: int = 0
        self.successful: int = 0
        self.failed: int = 0
        self.segments: int = 0
        self.qdrant_indexed: int = 0
        self.errors: list[dict] = []

    def summary(self) -> dict:
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "segments": self.segments,
            "qdrant_indexed": self.qdrant_indexed,
            "errors": self.errors[:50],
        }


async def run(
    source_dir: str,
    db: AsyncSession,
    pipeline: SegmentationPipeline,
    *,
    method: str = "kmeans",
    limit: int = 0,
) -> dict:
    """Execute a batch import from a directory of images.

    Args:
        source_dir: Path to directory containing images (recursive).
        db: Async SQLAlchemy session.
        pipeline: SegmentationPipeline instance.
        method: Segmentation method ('kmeans' or 'contour').
        limit: Max images to process (0 = all).

    Returns:
        Dict with summary counters.
    """
    result = BatchImportResult()
    qdrant_svc = QdrantClientService()
    source = Path(source_dir)

    if not source.exists() or not source.is_dir():
        return {"error": f"Source directory not found: {source_dir}"}

    # Collect all image paths
    image_paths: list[Path] = []
    for img_path in sorted(source.rglob("*")):
        if not img_path.is_file():
            continue
        if img_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if img_path.name.lower() in SKIP_NAMES:
            continue
        if _is_artifact_filename(img_path.name):
            continue
        image_paths.append(img_path)

    if limit > 0:
        image_paths = image_paths[:limit]

    result.total = len(image_paths)
    logger.info("Starting batch import: %d images from %s", result.total, source_dir)

    for i, img_path in enumerate(image_paths):
        logger.info("[%d/%d] Processing: %s", i + 1, result.total, img_path.name)
        try:
            # Step 1: Parse metadata
            meta = _parse_filename_metadata(
                img_path.name, str(img_path.relative_to(source))
            )
            logger.info(
                "  parsed: species=%s strain=%s media=%s angle=%s",
                meta.get("species"),
                meta.get("strain"),
                meta.get("media"),
                meta.get("angle"),
            )

            if _is_artifact_species(meta.get("species", "")):
                result.failed += 1
                result.errors.append(
                    {
                        "file": str(img_path),
                        "error": f"Rejected: species name '{meta.get('species')}' is an artifact filename",
                    }
                )
                logger.warning(
                    "  SKIP: species '%s' looks like artifact filename",
                    meta.get("species"),
                )
                continue

            # Step 2: Segment image
            record = pipeline.segment_upload(
                img_path,
                strain=meta.get("strain", "unknown"),
                media=meta.get("media", "unknown"),
                method=method,
            )
            logger.info("  segmented: %d colonies found", len(record.segments))

            # Step 3: Persist to PostgreSQL
            species_obj = await _ensure_species(db, meta.get("species", "unknown"))
            media_obj = await _ensure_media(db, meta.get("media", "unknown"))
            strain_obj = await _ensure_strain(
                db, meta.get("strain", "unknown"), species_obj.id
            )
            image_obj = await _create_image(
                db, record, strain_obj, species_obj, media_obj
            )
            logger.info("  db: image_id=%s", str(image_obj.id))

            # Step 4: Extract features + index to Qdrant
            indexed_count = 0
            for seg in image_obj.segments:
                try:
                    crop_path = Path(seg.crop_path)
                    if not crop_path.exists():
                        logger.warning("  crop not found: %s", crop_path)
                        continue

                    vectors = extract_features(crop_path)
                    if not vectors:
                        continue

                    import uuid

                    point_id = uuid.uuid4().int & ((1 << 63) - 1)
                    await qdrant_svc.upsert_point(
                        point_id=point_id,
                        vectors=vectors,
                        payload={
                            "segment_id": str(seg.id),
                            "image_id": str(image_obj.id),
                            "segment_index": seg.segment_index,
                            "bbox": {
                                "x": seg.bbox_x,
                                "y": seg.bbox_y,
                                "w": seg.bbox_w,
                                "h": seg.bbox_h,
                            },
                            "species": species_obj.name,
                            "strain": strain_obj.name,
                        },
                    )

                    seg.qdrant_point_id = UUID(int=point_id)
                    qis = QdrantIndexState(
                        segment_id=seg.id,
                        qdrant_point_id=seg.qdrant_point_id,
                        collection_name="myco_fungi_features_full_finetuned",
                        is_active=True,
                    )
                    db.add(qis)
                    indexed_count += 1
                    logger.info(
                        "  qdrant: indexed segment %d → point %d",
                        seg.segment_index,
                        point_id,
                    )
                except Exception as exc:
                    logger.error(
                        "  qdrant index failed for segment %d: %s",
                        seg.segment_index,
                        exc,
                    )

            await db.flush()
            result.successful += 1
            result.segments += len(record.segments)
            result.qdrant_indexed += indexed_count

        except Exception as e:
            result.failed += 1
            result.errors.append({"file": str(img_path), "error": str(e)})
            logger.error("  FAIL '%s': %s", img_path.name, str(e)[:200])

    await db.commit()
    summary = result.summary()
    logger.info("Batch import complete: %s", summary)
    return summary


# ---------------------------------------------------------------------------
# DB helpers (mirrored from routes.py for standalone use)
# ---------------------------------------------------------------------------


async def _ensure_species(db: AsyncSession, name: str) -> Species:
    result = await db.execute(select(Species).where(Species.name == name))
    sp = result.scalar_one_or_none()
    if sp:
        return sp
    sp = Species(name=name)
    db.add(sp)
    await db.flush()
    return sp


async def _ensure_media(db: AsyncSession, name: str) -> Media:
    result = await db.execute(select(Media).where(Media.name == name))
    md = result.scalar_one_or_none()
    if md:
        return md
    md = Media(name=name)
    db.add(md)
    await db.flush()
    return md


async def _ensure_strain(db: AsyncSession, name: str, species_id: UUID) -> Strain:
    result = await db.execute(
        select(Strain).where(Strain.name == name, Strain.species_id == species_id)
    )
    st = result.scalar_one_or_none()
    if st:
        return st
    st = Strain(name=name, species_id=species_id, source="batch_import")
    db.add(st)
    await db.flush()
    return st


async def _create_image(
    db: AsyncSession,
    record,
    strain_obj: Strain,
    species_obj: Species,
    media_obj: Media,
) -> Image:
    img = Image(
        strain_id=strain_obj.id,
        species_id=species_obj.id,
        media_id=media_obj.id,
        file_path=str(record.source_path),
        prepared_path=str(record.artifact_dir / "prepared.jpg"),
        pipeline_path=str(
            record.artifact_dir / f"pipeline_{record.segmentation_method}.jpg"
        ),
        data_update_status="current",
    )
    db.add(img)
    await db.flush()

    for seg in record.segments:
        segment = Segment(
            image_id=img.id,
            segment_index=seg.segment_index,
            crop_path=str(
                record.artifact_dir / "segments" / f"segment_{seg.segment_index}.jpg"
            ),
            bbox_x=seg.bbox.x,
            bbox_y=seg.bbox.y,
            bbox_w=seg.bbox.w,
            bbox_h=seg.bbox.h,
            segmentation_method=record.segmentation_method,
        )
        db.add(segment)

    await db.flush()
    return img


# ---------------------------------------------------------------------------
# Metadata parser (ported from research/parser.py + dto_import.py)
# ---------------------------------------------------------------------------


def _is_artifact_filename(filename: str) -> bool:
    """Check if a filename is a segmentation/processing artifact, not a source image."""
    lower = filename.lower()
    artifact_patterns = [
        r"^segment_\d+\.(jpg|jpeg|png|jpe)$",
        r"^prepared\.(jpg|jpeg|png|jpe)$",
        r"^source\.(jpg|jpeg|png|jpe)$",
        r"^bbox_.*\.(jpg|jpeg|png|jpe)$",
        r"^pipeline_.*\.(jpg|jpeg|png|jpe)$",
    ]
    return any(re.match(p, lower) for p in artifact_patterns)


def _is_artifact_species(name: str) -> bool:
    """Reject species names that are clearly not real species."""
    lower = name.strip().lower()
    if lower in {
        "unknown",
        "img1",
        "img2",
        "source",
        "prepared",
        "none",
        "n/a",
        "test",
    }:
        return True
    if re.match(r"^segment_\d+$", lower) or re.match(r"^seg_\d+$", lower):
        return True
    if lower.startswith("pipeline_") or lower.startswith("bbox_"):
        return True
    if lower.endswith("_kmeans"):
        return True
    if re.match(r"^dscn\d+", lower):
        return True
    if re.match(r"^img[_\s-]?\d+$", lower):
        return True
    if lower.startswith("test-") or lower.startswith("text-"):
        return True
    if re.match(r"^t\d+$", lower) or re.match(r"^t\(\d+\)$", lower):
        return True
    if re.match(r"^dto\s*[\d\-]", lower):
        return True
    if re.search(r"\b(cbs|ibt|nrrl|dto)\s*\d", lower):
        return True
    return False


def _normalize_angle(raw: str) -> str:
    """Normalize angle codes: o→ob, r→rev, pass through ob/rev."""
    mapping = {"o": "ob", "r": "rev", "ob": "ob", "rev": "rev"}
    return mapping.get(raw.lower(), "unknown")


def _parse_filename_metadata(filename: str, rel_path: str = "") -> dict[str, str]:
    """Extract species, strain, media, angle from filename and folder path.

    Handles DTO format:  DTO 148-C8 CYAob_edited.jpg → DTO 148-C8, CYA, ob
    And standard format: species CBS 123 CYAo.jpg → species, CBS 123, CYA, ob
    Also supports: T491 MEA rev.JPG → T491, MEA, rev
    """
    base = filename.rsplit(".", 1)[0]
    lower = base.lower()

    media = "unknown"
    angle = "unknown"
    species = "unknown"
    strain = "unknown"

    # Strategy 1: "MEDIA[or]" suffix (CYAo, MEAr, YESob, etc.)
    m_suffix = re.search(
        r"\b(cya30|cyas|cya|mea|yes|dg18|crea|oa|m40y)(ob|rev|o|r)",
        lower,
    )
    if m_suffix:
        raw_media = m_suffix.group(1).upper()
        if raw_media in ("CYA30", "CYAS"):
            media = "CYA"
        else:
            media = raw_media
        raw_angle = m_suffix.group(2).lower()
        angle = _normalize_angle(raw_angle)
        rest = lower[: m_suffix.start()].strip()
    else:
        # Strategy 2: "MEDIA ANGLE" space-separated
        m_angle = re.search(r"(cya|mea|yes|dg18|crea|oa|m40y)\s+(ob|rev)\b", lower)
        if m_angle:
            media = m_angle.group(1).upper()
            angle = m_angle.group(2)
            rest = lower[: m_angle.start()].strip()
        else:
            rest = lower

    # Remove _edited suffix common in DTO dataset
    rest = re.sub(r"_edited$", "", rest, flags=re.IGNORECASE)

    # Extract strain code (DTO, CBS, IBT, T-number, NRRL)
    m_strain = re.search(
        r"\b(DTO\s+[\d\-A-Za-z]+)\b|"
        r"\b(CBS\s+[\d_/]+)\b|"
        r"\b(IBT\s+\d+)\b|"
        r"\b(NRRL\s+\d+)\b|"
        r"\b(T\d+)\b",
        rest,
        re.IGNORECASE,
    )
    if m_strain:
        strain = m_strain.group(0).upper()
        # Species is everything before the strain code
        species = rest[: m_strain.start()].strip()
    else:
        # No strain found — the rest is the species name
        species = rest.strip()

    # Clean up species name
    species = species.strip().strip("_-").strip()
    if not species:
        species = "unknown"

    # Fallback: extract species/strain from folder path (DTO folder format)
    if (species == "unknown" or species == "") and rel_path:
        m_dto_folder = re.search(
            r"DTO\s+[\d\-A-Za-z]+\s+(Penicillium\s+\w+(?:\s+\w+)*)",
            rel_path,
            re.IGNORECASE,
        )
        if m_dto_folder:
            species = m_dto_folder.group(1).strip()
            # Re-extract strain from the DTO code
            m_dto_strain = re.search(r"(DTO\s+[\d\-A-Za-z]+)", rel_path, re.IGNORECASE)
            if m_dto_strain:
                strain = (
                    m_dto_strain.group(1).upper() if strain == "unknown" else strain
                )

    if not species or species == "unknown":
        # Last resort: use folder path
        parts = [p for p in Path(rel_path).parts if p]
        alpha_patterns = {
            "A - C",
            "D - L",
            "M - R",
            "S - Z",
            "A-C",
            "D-L",
            "M-R",
            "S-Z",
        }
        meaningful = [
            p for p in parts if p not in alpha_patterns and not p.endswith(".jpg")
        ]
        if len(meaningful) >= 2:
            species = meaningful[-2]
        elif len(meaningful) >= 1:
            species = meaningful[0]

    return {
        "species": species or "unknown",
        "strain": strain or "unknown",
        "media": media or "unknown",
        "angle": angle or "unknown",
    }
