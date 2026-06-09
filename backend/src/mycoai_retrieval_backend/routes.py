"""
Image routes with DB persistence + file storage + segmentation.

POST /api/v1/images          – upload single image (segment + db)
GET  /api/v1/images/{id}     – get image detail from db
POST /api/v1/images/batch    – import batch from folder
"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .core.dependencies import get_current_user, require_owner
from .database import get_db
from .image_models import BoundingBox, ImageRecord, ImageResponse
from .image_models import Segment as SegModel
from .models import Image, Media, Segment, Species, Strain
from .schemas import ImageListItem, ImageListResponse
from .segmentation import ImageStore as FileStore
from .segmentation import SegmentationPipeline


class BatchImportRequest(BaseModel):
    source_dir: str
    method: str = "kmeans"


def create_image_router(
    *,
    store: FileStore,
    pipeline: SegmentationPipeline,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/images", tags=["images"])

    # ------------------------------------------------------------------
    # List images with filters
    # ------------------------------------------------------------------
    @router.get("", response_model=ImageListResponse)
    async def list_images(
        species_id: Annotated[list[str] | None, Query()] = None,
        media_id: Annotated[list[str] | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
        search: Annotated[str | None, Query()] = None,
        include_archived: Annotated[bool, Query()] = False,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=200)] = 50,
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageListResponse:
        stmt = (
            select(Image)
            .options(
                selectinload(Image.strain),
                selectinload(Image.species),
                selectinload(Image.media),
                selectinload(Image.segments).selectinload(Segment.qdrant_index_state),
            )
        )

        if not include_archived:
            stmt = stmt.where(Image.is_archived.is_(False))

        if species_id:
            species_uuids = []
            for sid in species_id:
                try:
                    species_uuids.append(UUID(sid))
                except ValueError:
                    pass
            if species_uuids:
                stmt = stmt.where(Image.species_id.in_(species_uuids))

        if media_id:
            media_uuids = []
            for mid in media_id:
                try:
                    media_uuids.append(UUID(mid))
                except ValueError:
                    pass
            if media_uuids:
                stmt = stmt.where(Image.media_id.in_(media_uuids))

        if status:
            stmt = stmt.where(Image.data_update_status == status)

        if search:
            stmt = stmt.join(Image.strain).where(Strain.name.ilike(f"%{search}%"))

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.order_by(Image.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        images = result.unique().scalars().all()

        items: list[ImageListItem] = []
        for img in images:
            # Determine if any segment is indexed in qdrant
            indexed = any(
                seg.qdrant_index_state is not None and seg.qdrant_index_state.is_active
                for seg in img.segments
            ) if img.segments else False

            items.append(ImageListItem(
                id=str(img.id),
                strain_name=img.strain.name if img.strain else "unknown",
                species_id=str(img.species_id),
                species_name=img.species.name if img.species else "unknown",
                media_id=str(img.media_id),
                media_name=img.media.name if img.media else "unknown",
                file_path=img.file_path,
                angle=img.angle,
                segments_count=len(img.segments) if img.segments else 0,
                data_update_status=img.data_update_status,
                indexed_in_qdrant=indexed,
                is_archived=img.is_archived,
                created_at=img.created_at,
            ))

        return ImageListResponse(items=items, total=total)

    # ------------------------------------------------------------------
    # Upload single image with segmentation
    # ------------------------------------------------------------------
    @router.post("", response_model=ImageResponse, status_code=201)
    async def upload_image(
        image: Annotated[UploadFile, File(...)],
        strain: Annotated[str, Form()] = "unknown-strain",
        media: Annotated[str, Form()] = "unknown-media",
        species: Annotated[str, Form()] = "unknown-species",
        method: Annotated[str, Form()] = "kmeans",
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageResponse:
        suffix = Path(image.filename or "source.jpg").suffix or ".jpg"
        with NamedTemporaryFile(suffix=suffix, delete=False) as handle:
            temp_path = Path(handle.name)
            while chunk := await image.read(1024 * 1024):
                handle.write(chunk)
        try:
            record = pipeline.segment_upload(
                temp_path,
                strain=strain,
                media=media,
                method=method,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            temp_path.unlink(missing_ok=True)

        # Persist to DB
        species_obj = await _ensure_species(db, species)
        media_obj = await _ensure_media(db, media)
        strain_obj = await _ensure_strain(db, strain, species_obj.id)
        image_obj = await _create_image(db, record, strain_obj, species_obj, media_obj)

        # Link DB IDs back to record response
        record.image_id = str(image_obj.id)
        store.add(record)

        return ImageResponse.model_validate(record.model_dump())

    # ------------------------------------------------------------------
    # Batch import from folder (owner only)
    # ------------------------------------------------------------------
    @router.post("/batch", status_code=202)
    async def batch_import(
        data: BatchImportRequest,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict:
        source = Path(data.source_dir)
        if not source.exists() or not source.is_dir():
            raise HTTPException(status_code=422, detail="Source directory not found")

        results: list[dict] = []
        errors: list[dict] = []

        for img_path in sorted(source.rglob("*")):
            if not img_path.is_file():
                continue
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".jpe"}:
                continue
            if img_path.name.lower() in {"thumbs.db", ".ds_store", "desktop.ini"}:
                continue

            # Parse from filename: species strain media angle
            # Also use folder structure as fallback for species
            rel_path = img_path.relative_to(source)
            meta = _parse_filename_metadata(img_path.name, str(rel_path))

            try:
                record = pipeline.segment_upload(
                    img_path,
                    strain=meta.get("strain", "unknown"),
                    media=meta.get("media", "unknown"),
                    method=data.method,
                )
                species_obj = await _ensure_species(db, meta.get("species", "unknown"))
                media_obj = await _ensure_media(db, meta.get("media", "unknown"))
                strain_obj = await _ensure_strain(
                    db, meta.get("strain", "unknown"), species_obj.id
                )
                image_obj = await _create_image(
                    db, record, strain_obj, species_obj, media_obj
                )

                results.append(
                    {
                        "image_id": str(image_obj.id),
                        "strain": strain_obj.name,
                        "media": media_obj.name,
                        "species": species_obj.name,
                        "segments": len(record.segments),
                    }
                )
            except Exception as e:
                errors.append({"file": str(img_path), "error": str(e)})

        return {
            "status": "completed",
            "total": len(results) + len(errors),
            "successful": len(results),
            "failed": len(errors),
            "results": results[:100],
            "errors": errors[:50],
        }

    # ------------------------------------------------------------------
    # Get image detail
    # ------------------------------------------------------------------
    @router.get("/{image_id}", response_model=ImageResponse)
    async def get_image(
        image_id: str,
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageResponse:
        # First try in-memory store (latest uploads)
        record = store.get(image_id)
        if record:
            return ImageResponse.model_validate(record.model_dump())

        # Try DB
        try:
            img_uuid = UUID(image_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="image not found") from err

        result = await db.execute(
            select(Image)
            .options(
                selectinload(Image.segments),
                selectinload(Image.strain),
                selectinload(Image.media),
            )
            .where(Image.id == img_uuid)
        )
        img = result.scalar_one_or_none()
        if not img:
            raise HTTPException(status_code=404, detail="image not found")

        segments = [
            SegModel(
                segment_id=f"{img.id}:{seg.segment_index}",
                segment_index=seg.segment_index,
                bbox=BoundingBox(
                    x=seg.bbox_x, y=seg.bbox_y, w=seg.bbox_w, h=seg.bbox_h
                ),
                crop_url=f"/api/v1/images/{img.id}/segments/{seg.segment_index}/crop",
                pipeline_url=f"/api/v1/images/{img.id}/pipeline?method={seg.segmentation_method}",
            )
            for seg in img.segments
        ]

        artifact_dir = Path(img.file_path).parent
        record = ImageRecord(
            image_id=str(img.id),
            source_path=Path(img.file_path),
            artifact_dir=artifact_dir,
            source_url=f"/static/{img.strain.name}/{img.media.name}/{img.id}/source.jpg",
            segments=segments,
            segmentation_method=img.segments[0].segmentation_method
            if img.segments
            else "kmeans",
        )
        return ImageResponse.model_validate(record.model_dump())

    # ------------------------------------------------------------------
    # PATCH segments
    # ------------------------------------------------------------------
    @router.patch("/{image_id}/segments", response_model=ImageResponse)
    async def update_segments(
        image_id: str,
        patch,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> ImageResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        updated = pipeline.update_segments(record, patch)
        store.add(updated)
        return ImageResponse.model_validate(updated.model_dump())

    # ------------------------------------------------------------------
    # GET segment crop
    # ------------------------------------------------------------------
    @router.get("/{image_id}/segments/{segment_index}/crop")
    def get_crop(image_id: str, segment_index: int) -> FileResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        crop_path = record.artifact_dir / "segments" / f"segment_{segment_index}.jpg"
        if not crop_path.exists():
            raise HTTPException(status_code=404, detail="segment not found")
        return FileResponse(crop_path)

    # ------------------------------------------------------------------
    # GET pipeline image
    # ------------------------------------------------------------------
    @router.get("/{image_id}/pipeline")
    def get_pipeline(image_id: str, method: str = "kmeans") -> FileResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        pipeline_path = record.artifact_dir / f"pipeline_{method}.jpg"
        if not pipeline_path.exists():
            raise HTTPException(status_code=404, detail="pipeline image not found")
        return FileResponse(pipeline_path)

    # ------------------------------------------------------------------
    # DELETE image (soft delete)
    # ------------------------------------------------------------------
    @router.delete("/{image_id}", status_code=204)
    async def delete_image(
        image_id: str,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> None:
        try:
            img_uuid = UUID(image_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="image not found") from err

        result = await db.execute(select(Image).where(Image.id == img_uuid))
        img = result.scalar_one_or_none()
        if not img:
            raise HTTPException(status_code=404, detail="image not found")
        img.is_archived = True
        await db.commit()

    return router


# ---------------------------------------------------------------------------
# DB helpers
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
    st = Strain(name=name, species_id=species_id, source="user_upload")
    db.add(st)
    await db.flush()
    return st


async def _create_image(
    db: AsyncSession,
    record: ImageRecord,
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

    await db.commit()
    return img


def _parse_filename_metadata(filename: str, rel_path: str = "") -> dict[str, str]:
    """Extract species, strain, media, angle from filename and folder path.

    Uses filename patterns first, then falls back to folder hierarchy:
      species/strain/file.jpg  or  alpha/species/strain/file.jpg
    """
    import re

    base = filename.rsplit(".", 1)[0]
    lower = base.lower()

    media = "unknown"
    angle = "unknown"
    species = "unknown"
    strain = "unknown"

    # Try "MEDIA[or]" suffix pattern first (most common)
    m_suffix = re.search(r"\b(cya|mea|yes|dg18|crea|oa|m40y)(o|r)\b", lower)
    if m_suffix:
        media = m_suffix.group(1).upper()
        angle = "ob" if m_suffix.group(2) == "o" else "rev"
        rest = lower[: m_suffix.start()].strip()
    else:
        # Try "MEDIA ANGLE" pattern
        m_angle = re.search(r"(cya|mea|yes|dg18|crea|oa|m40y)\s+(ob|rev)\b", lower)
        if m_angle:
            media = m_angle.group(1).upper()
            angle = m_angle.group(2)
            rest = lower[: m_angle.start()].strip()
        else:
            rest = lower

    # Extract strain (CBS/IBT/T/DTO pattern)
    m_strain = re.search(
        r"\b(T\d+)\b|\b(CBS\s+[\d_/]+)\b|\b(IBT\s+\d+)\b|\b(DTO\s+[\d\-A-Za-z]+)\b",
        rest,
        re.IGNORECASE,
    )
    if m_strain:
        strain = m_strain.group(0).upper()
        species = rest[: m_strain.start()].strip()
    else:
        species = rest.strip()

    if not species or species == "unknown":
        species = rest.strip()

    # Fallback: extract species/strain from folder path
    if (not species or species == "unknown") and rel_path:
        parts = [p for p in Path(rel_path).parts if p]
        # Skip alpha group folders like "D - L", "M - R", etc.
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
            strain = meaningful[-1] if strain == "unknown" else strain
        elif len(meaningful) >= 1:
            species = meaningful[0]

    if not species:
        species = "unknown"

    return {"species": species, "strain": strain, "media": media, "angle": angle}
