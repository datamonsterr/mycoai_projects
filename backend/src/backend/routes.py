"""
Image routes with DB persistence + file storage + segmentation.

POST /api/v1/images              − upload single image (segment + db)
POST /api/v1/images/upload       − alias for single image upload
GET  /api/v1/images/{id}         − get image detail from db
POST /api/v1/images/batch        − import batch from server folder
POST /api/v1/images/batch-upload − upload folder (multipart files + metadata)
POST /api/v1/images/batch-zip    − upload ZIP batch (extract + segment + db)
"""

from __future__ import annotations

import json
import logging
import shutil
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from typing import TYPE_CHECKING, Annotated, Any
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
from .segmentation import ALLOWED_METHODS, SegmentationPipeline
from .segmentation import ImageStore as FileStore
from .services.feature_extraction import index_segment_to_qdrant

if TYPE_CHECKING:
    from .services.storage import ObjectStorage

logger = logging.getLogger(__name__)


class BatchImportRequest(BaseModel):
    source_dir: str
    method: str = "kmeans"


class AutoSegmentRequest(BaseModel):
    method: str = "kmeans"


def create_image_router(
    *,
    store: FileStore,
    pipeline: SegmentationPipeline,
    storage: ObjectStorage | None = None,
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
        stmt = select(Image).options(
            selectinload(Image.strain),
            selectinload(Image.species),
            selectinload(Image.media),
            selectinload(Image.segments).selectinload(Segment.qdrant_index_state),
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
            indexed = (
                any(
                    seg.qdrant_index_state is not None
                    and seg.qdrant_index_state.is_active
                    for seg in img.segments
                )
                if img.segments
                else False
            )

            source_url: str
            if storage:
                candidate = storage.get_url(img.file_path)
                if candidate.startswith(("http://", "https://")):
                    source_url = candidate.replace(
                        "http://minio:9000/", "/minio/"
                    )
                else:
                    source_url = f"/api/v1/images/{img.id}/source"
            else:
                source_url = f"/api/v1/images/{img.id}/source"

            items.append(
                ImageListItem(
                    id=str(img.id),
                    strain_name=img.strain.name if img.strain else "unknown",
                    species_id=str(img.species_id),
                    species_name=img.species.name if img.species else "unknown",
                    media_id=str(img.media_id),
                    media_name=img.media.name if img.media else "unknown",
                    file_path=img.file_path,
                    source_url=source_url,
                    angle=img.angle,
                    segments_count=len(img.segments) if img.segments else 0,
                    data_update_status=img.data_update_status,
                    indexed_in_qdrant=indexed,
                    is_archived=img.is_archived,
                    created_at=img.created_at,
                )
            )

        return ImageListResponse(items=items, total=total)

    # ------------------------------------------------------------------
    # Shared upload logic (used by both POST / and POST /upload)
    # ------------------------------------------------------------------
    async def _do_upload_image(
        image: UploadFile,
        strain: str,
        media: str,
        species: str,
        method: str,
        db: AsyncSession,
        user,
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

        species_obj = await _ensure_species(db, species)
        media_obj = await _ensure_media(db, media)
        strain_obj = await _ensure_strain(db, strain, species_obj.id)
        image_obj = await _create_image(db, record, strain_obj, species_obj, media_obj)

        # Index segments to Qdrant with feature vectors
        for seg in image_obj.segments:
            try:
                await index_segment_to_qdrant(
                    db,
                    seg,
                    image_obj,
                    strain_name=strain_obj.name,
                    species_name=species_obj.name,
                    media_name=media_obj.name,
                    storage=storage,
                )
            except Exception as exc:
                logger.warning("Qdrant index failed for segment %s: %s", seg.id, exc)

        record.image_id = str(image_obj.id)
        record.source_url = f"/api/v1/images/{record.image_id}/source"
        for seg in record.segments:
            seg.crop_url = (
                f"/api/v1/images/{record.image_id}"
                f"/segments/{seg.segment_index}/crop"
            )
            seg.pipeline_url = (
                f"/api/v1/images/{record.image_id}"
                f"/pipeline?method={record.segmentation_method}"
            )
        store.add(record)

        return ImageResponse.model_validate(record.model_dump())

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
        return await _do_upload_image(image, strain, media, species, method, db, user)

    # ------------------------------------------------------------------
    # Upload single image (alias: /upload — matches frontend + docs)
    # ------------------------------------------------------------------
    @router.post("/upload", response_model=ImageResponse, status_code=201)
    async def upload_image_alias(
        image: Annotated[UploadFile, File(...)],
        strain: Annotated[str, Form()] = "unknown-strain",
        media: Annotated[str, Form()] = "unknown-media",
        species: Annotated[str, Form()] = "unknown-species",
        method: Annotated[str, Form()] = "kmeans",
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageResponse:
        return await _do_upload_image(image, strain, media, species, method, db, user)

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
            if _is_artifact_filename(img_path.name):
                continue

            # Parse from filename: species strain media angle
            # Also use folder structure as fallback for species
            rel_path = img_path.relative_to(source)
            meta = _parse_filename_metadata(img_path.name, str(rel_path))

            # Reject species names that look like artifact filenames
            if _is_artifact_species(meta.get("species", "")):
                errors.append(
                    {
                        "file": str(img_path),
                        "error": (
                            f"Rejected: species name "
                            f"'{meta.get('species')}' is an artifact filename"
                        ),
                    }
                )
                continue

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
                        "source_url": f"/api/v1/images/{image_obj.id}/source",
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
    # Batch folder upload: client sends folder as multiple files.
    # Expected: mycoai_new_species/{strain}/{image}, optional metadata JSON
    @router.post("/batch-upload", status_code=202)
    async def batch_folder_upload(
        files: Annotated[list[UploadFile], File(...)],
        metadata: Annotated[str | None, Form()] = None,
        default_media: Annotated[str, Form()] = "MEA",
        default_species: Annotated[str, Form()] = "unknown-species",
        method: Annotated[str, Form()] = "kmeans",
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> dict[str, Any]:
        batch_meta: dict[str, Any] = {}
        if metadata:
            try:
                batch_meta = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=422, detail="Invalid metadata JSON"
                ) from None

        batch_name = batch_meta.get("batch_name", "batch")
        strain_meta: dict[str, dict[str, str]] = batch_meta.get("strains", {})

        # Process each uploaded file
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        temp_files: list[Path] = []

        for upload_file in files:
            filename = upload_file.filename or "unknown.jpg"
            suffix = Path(filename).suffix.lower()

            # Skip non-image files and hidden/system files
            if suffix not in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp"}:
                if suffix not in {".json", ".csv", ".txt", ".md"}:
                    continue

            if Path(filename).name.lower() in {"thumbs.db", ".ds_store", "desktop.ini"}:
                continue

            # Extract strain from path: mycoai_new_species/{strain}/{image_name}
            parts = Path(filename).parts
            strain = "unknown-strain"
            if len(parts) >= 2:
                # First part is root folder name, second part is strain
                strain = parts[1] if parts[0] else parts[0]

            # Parse filename metadata (species, media, angle)
            meta = _parse_filename_metadata(Path(filename).name, filename)
            strain_from_meta = meta.get("strain", "unknown")
            if strain_from_meta != "unknown":
                strain = strain_from_meta
            species = meta.get("species", default_species)
            media_name = meta.get("media", default_media)
            if media_name == "unknown":
                media_name = default_media

            # Check strain-specific overrides from metadata JSON
            if strain in strain_meta:
                sm = strain_meta[strain]
                species = sm.get("species", species)
                media_name = sm.get("media", media_name)

            # Save to temp file and process
            with NamedTemporaryFile(suffix=suffix, delete=False) as handle:
                temp_path = Path(handle.name)
                while chunk := await upload_file.read(1024 * 1024):
                    handle.write(chunk)
            temp_files.append(temp_path)

            try:
                record = pipeline.segment_upload(
                    temp_path,
                    strain=strain,
                    media=media_name,
                    method=method,
                )
                species_obj = await _ensure_species(db, species)
                media_obj = await _ensure_media(db, media_name)
                strain_obj = await _ensure_strain(db, strain, species_obj.id)
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
                        "filename": filename,
                        "source_url": f"/api/v1/images/{image_obj.id}/source",
                    }
                )
            except Exception as e:
                errors.append({"file": filename, "error": str(e)})

        # Cleanup temp files
        for tf in temp_files:
            tf.unlink(missing_ok=True)

        return {
            "status": "completed",
            "batch_name": batch_name,
            "total": len(results) + len(errors),
            "successful": len(results),
            "failed": len(errors),
            "results": results[:200],
            "errors": errors[:100],
        }

    # ------------------------------------------------------------------
    # Batch ZIP upload: accept a ZIP file, extract, segment, and persist
    # ------------------------------------------------------------------
    @router.post("/batch-zip", status_code=202)
    async def batch_zip_upload(
        zipfile_file: Annotated[UploadFile, File(alias="zipfile")],
        default_media: Annotated[str, Form()] = "MEA",
        default_species: Annotated[str, Form()] = "unknown-species",
        method: Annotated[str, Form()] = "kmeans",
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict[str, Any]:
        if (
            not zipfile_file.filename
            or not zipfile_file.filename.lower().endswith(".zip")
        ):
            raise HTTPException(
                status_code=422, detail="Only .zip files are accepted"
            )

        work_dir = Path(mkdtemp(prefix="batch_zip_"))
        zip_path = work_dir / "upload.zip"
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        try:
            # Save uploaded ZIP to temp file
            with zip_path.open("wb") as out:
                while chunk := await zipfile_file.read(1024 * 1024):
                    out.write(chunk)

            # Extract ZIP
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(work_dir)

            # Find all image files in extracted content
            image_extensions = {".jpg", ".jpeg", ".png", ".jpe"}
            skip_names = {"thumbs.db", ".ds_store", "desktop.ini", ".gitkeep"}
            image_files: list[Path] = []

            for img_path in sorted(work_dir.rglob("*")):
                if not img_path.is_file():
                    continue
                if img_path == zip_path:
                    continue
                if img_path.suffix.lower() not in image_extensions:
                    continue
                if img_path.name.lower() in skip_names:
                    continue
                if _is_artifact_filename(img_path.name):
                    continue
                image_files.append(img_path)

            batch_name = Path(zipfile_file.filename or "batch").stem

            for img_path in image_files:
                try:
                    # Extract strain from folder structure: .../images/{strain}/file.jpg
                    rel_path = img_path.relative_to(work_dir)
                    strain = _extract_strain_from_path(rel_path)
                    meta = _parse_filename_metadata(img_path.name, str(rel_path))
                    media_name = meta.get("media", default_media)
                    if media_name == "unknown":
                        media_name = default_media
                    species = meta.get("species", default_species)

                    record = pipeline.segment_upload(
                        img_path,
                        strain=strain,
                        media=media_name,
                        method=method,
                    )
                    species_obj = await _ensure_species(db, species)
                    media_obj = await _ensure_media(db, media_name)
                    strain_obj = await _ensure_strain(db, strain, species_obj.id)
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
                            "filename": str(rel_path),
                            "source_url": f"/api/v1/images/{image_obj.id}/source",
                        }
                    )
                except Exception as e:
                    errors.append({
                        "file": str(img_path.relative_to(work_dir)),
                        "error": str(e),
                    })

        except zipfile.BadZipFile:
            raise HTTPException(
                status_code=422, detail="Invalid or corrupted ZIP file"
            ) from None
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

        return {
            "status": "completed",
            "batch_name": batch_name,
            "total": len(results) + len(errors),
            "successful": len(results),
            "failed": len(errors),
            "results": results[:200],
            "errors": errors[:100],
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
            source_url=(
                f"/api/v1/images/{img.id}/source"
                if storage
                else f"/static/{img.strain.name}/{img.media.name}/{img.id}/source.jpg"
            ),
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
    # POST auto-segment (kmeans / contour / yolo)
    # ------------------------------------------------------------------
    @router.post("/{image_id}/segment", response_model=ImageResponse)
    async def auto_segment(
        image_id: str,
        body: AutoSegmentRequest = AutoSegmentRequest(),
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageResponse:
        if body.method not in ALLOWED_METHODS:
            allowed = sorted(ALLOWED_METHODS)
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported method '{body.method}'. Allowed: {allowed}",
            )

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

        source_path = Path(img.file_path)
        _cleanup_source = False

        if storage:
            source_bytes = _read_source_from_storage(storage, img, source_path)
            if source_bytes is None:
                raise HTTPException(
                    status_code=404, detail="source file not found in storage"
                )
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp.write(source_bytes)
                source_path = Path(tmp.name)
                _cleanup_source = True
        elif not source_path.exists():
            raise HTTPException(status_code=404, detail="source file not found on disk")

        strain_name = img.strain.name if img.strain else "unknown"
        media_name = img.media.name if img.media else "unknown"

        try:
            # Run segmentation
            record = pipeline.segment_upload(
                source_path,
                strain=strain_name,
                media=media_name,
                method=body.method,
            )
        finally:
            if storage and _cleanup_source:
                source_path.unlink(missing_ok=True)

        # Delete old segments (unique constraint on image_id+segment_index)
        for seg in img.segments:
            await db.delete(seg)
        await db.flush()

        # Create new segments
        for seg_model in record.segments:
            segment = Segment(
                image_id=img.id,
                segment_index=seg_model.segment_index,
                crop_path=str(
                    record.artifact_dir
                    / "segments"
                    / f"segment_{seg_model.segment_index}.jpg"
                ),
                bbox_x=seg_model.bbox.x,
                bbox_y=seg_model.bbox.y,
                bbox_w=seg_model.bbox.w,
                bbox_h=seg_model.bbox.h,
                segmentation_method=body.method,
            )
            db.add(segment)

        img.data_update_status = "updated_requires_reindex"
        await db.commit()

        # Reload image with segments for indexing
        await db.refresh(img)
        result2 = await db.execute(
            select(Image)
            .options(selectinload(Image.segments), selectinload(Image.strain), selectinload(Image.species), selectinload(Image.media))
            .where(Image.id == img.id)
        )
        img_reloaded = result2.scalar_one_or_none()
        if img_reloaded:
            strain_name = img_reloaded.strain.name if img_reloaded.strain else "unknown"
            species_name = img_reloaded.species.name if img_reloaded.species else "unknown"
            media_name = img_reloaded.media.name if img_reloaded.media else "unknown"
            for seg in img_reloaded.segments:
                if seg.qdrant_point_id is None:
                    try:
                        await index_segment_to_qdrant(
                            db, seg, img_reloaded,
                            strain_name=strain_name,
                            species_name=species_name,
                            media_name=media_name,
                            storage=storage,
                        )
                    except Exception as exc:
                        logger.warning("Qdrant index failed for segment %s: %s", seg.id, exc)
            await db.commit()

        record.image_id = str(img.id)
        record.source_url = f"/api/v1/images/{record.image_id}/source"
        for seg in record.segments:
            seg.crop_url = (
                f"/api/v1/images/{record.image_id}"
                f"/segments/{seg.segment_index}/crop"
            )
            seg.pipeline_url = (
                f"/api/v1/images/{record.image_id}"
                f"/pipeline?method={record.segmentation_method}"
            )
        store.add(record)

        return ImageResponse.model_validate(record.model_dump())

    # ------------------------------------------------------------------
    # GET source image
    # ------------------------------------------------------------------
    @router.get("/{image_id}/source", response_model=None)
    async def get_source(
        image_id: str,
        db=Depends(get_db),
    ):
        record = store.get(image_id)
        if record:
            return _serve_storage_file(
                storage, record.artifact_dir, "source.jpg", record.source_url
            )

        try:
            img_uuid = UUID(image_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="image not found") from err

        result = await db.execute(
            select(Image).options(selectinload(Image.segments)).where(
                Image.id == img_uuid
            )
        )
        img = result.scalar_one_or_none()
        if not img:
            raise HTTPException(status_code=404, detail="image not found")
        source_path = Path(img.file_path)
        artifact_dir = source_path.parent
        return _serve_storage_file(storage, artifact_dir, "source.jpg", "")

    # ------------------------------------------------------------------
    # GET segment crop
    # ------------------------------------------------------------------
    @router.get(
        "/{image_id}/segments/{segment_index}/crop", response_model=None
    )
    async def get_crop(
        image_id: str,
        segment_index: int,
        db=Depends(get_db),
    ):
        record = store.get(image_id)
        if record:
            key = f"segments/segment_{segment_index}.jpg"
            return _serve_storage_file(storage, record.artifact_dir, key, "")

        try:
            img_uuid = UUID(image_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="image not found") from err

        result = await db.execute(
            select(Image)
            .options(selectinload(Image.segments))
            .where(Image.id == img_uuid)
        )
        img = result.scalar_one_or_none()
        if not img:
            raise HTTPException(status_code=404, detail="image not found")

        artifact_dir = Path(img.file_path).parent
        key = f"segments/segment_{segment_index}.jpg"
        return _serve_storage_file(storage, artifact_dir, key, "")

    # ------------------------------------------------------------------
    # GET pipeline image
    # ------------------------------------------------------------------
    @router.get("/{image_id}/pipeline", response_model=None)
    async def get_pipeline(
        image_id: str,
        method: str = "kmeans",
        db=Depends(get_db),
    ):
        record = store.get(image_id)
        if record:
            key = f"pipeline_{method}.jpg"
            return _serve_storage_file(storage, record.artifact_dir, key, "")

        try:
            img_uuid = UUID(image_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="image not found") from err

        result = await db.execute(
            select(Image).where(Image.id == img_uuid)
        )
        img = result.scalar_one_or_none()
        if not img:
            raise HTTPException(status_code=404, detail="image not found")

        source_path = Path(img.file_path)
        artifact_dir = source_path.parent
        key = f"pipeline_{method}.jpg"
        return _serve_storage_file(storage, artifact_dir, key, "")

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
# Storage-serving helper
# ---------------------------------------------------------------------------


def _serve_storage_file(
    storage: ObjectStorage | None,
    artifact_dir: Path,
    filename: str,
    fallback_url: str,
):
    if storage:
        key = f"{artifact_dir}/{filename}"
        data = storage.get_bytes(key)
        if data is not None:
            from fastapi.responses import Response

            return Response(content=data, media_type="image/jpeg")
        raise HTTPException(status_code=404, detail="file not found in storage")

    if artifact_dir.is_absolute():
        local_path = artifact_dir / filename
    else:
        local_path = Path("Dataset/uploads") / artifact_dir / filename
    if not local_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(local_path)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _read_source_from_storage(
    storage: ObjectStorage, img: Image, source_path: Path
) -> bytes | None:
    """Read source image bytes from S3 storage, trying multiple key patterns."""
    candidates = [
        str(source_path),
        f"{img.strain.name}/{img.media.name}/{img.id}/source.jpg",
        f"{img.strain.name}/{img.media.name}/{str(img.id)}/source.jpg",
    ]
    for key in candidates:
        data = storage.get_bytes(key)
        if data is not None:
            return data
    return None


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


def _is_artifact_filename(filename: str) -> bool:
    """Check if a filename is a segmentation/processing artifact, not a source image."""
    import re

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
    """Reject species names that are clearly not real species.

    Catches: artifact filenames, camera filenames, codes used as species,
    placeholders, single short words without proper capitalization.
    """
    import re

    lower = name.strip().lower()
    # Exact artifact/placeholder matches
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
    # Segment-like
    if re.match(r"^segment_\d+$", lower):
        return True
    if re.match(r"^seg_\d+$", lower):
        return True
    # Artifact suffixes
    if lower.startswith("pipeline_") or lower.startswith("bbox_"):
        return True
    if lower.endswith("_kmeans"):
        return True
    # Camera default filenames
    if re.match(r"^dscn\d+", lower):
        return True
    if re.match(r"^img[_\s-]?\d+$", lower):
        return True
    # Test/placeholder
    if lower.startswith("test-") or lower.startswith("text-"):
        return True
    # T-codes or DTO codes used as species (not enough info)
    if re.match(r"^t\d+$", lower) or re.match(r"^t\(\d+\)$", lower):
        return True
    if re.match(r"^dto\s*[\d\-]", lower):
        return True
    # Strain code embedded in species name (e.g., "dipodomiys cbs170_87")
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
    Standard format:     species CBS 123 CYAo.jpg → species, CBS 123, CYA, ob
    Also supports:       T491 MEA rev.JPG → T491, MEA, rev
    Folder fallback:     parent_dir/subdir/file.jpg
    """
    import re

    base = filename.rsplit(".", 1)[0]
    lower = base.lower()

    media = "unknown"
    angle = "unknown"
    species = "unknown"
    strain = "unknown"

    # Strategy 1: "MEDIA[or]" suffix pattern (CYAo, MEAr, YESob, etc.)
    m_suffix = re.search(
        r"\b(cya30|cyas|cya|mea|yes|dg18|crea|oa|m40y)(ob|rev|o|r)", lower
    )
    if m_suffix:
        raw_media = m_suffix.group(1).upper()
        media = "CYA" if raw_media in ("CYA30", "CYAS") else raw_media
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
        species = rest[: m_strain.start()].strip()
    else:
        species = rest.strip()

    species = species.strip().strip("_-").strip()

    # Fallback: extract species/strain from folder path (DTO folder format)
    if (not species or species == "unknown") and rel_path:
        m_dto = re.search(
            r"DTO\s+[\d\-A-Za-z]+\s+(Penicillium\s+\w+(?:\s+\w+)*)",
            rel_path,
            re.IGNORECASE,
        )
        if m_dto:
            species = m_dto.group(1).strip()
            m_code = re.search(r"(DTO\s+[\d\-A-Za-z]+)", rel_path, re.IGNORECASE)
            if m_code and strain == "unknown":
                strain = m_code.group(1).upper()

    if not species or species == "unknown":
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
            if strain == "unknown":
                strain = meaningful[-1]
        elif len(meaningful) >= 1:
            species = meaningful[0]

    return {
        "species": species or "unknown",
        "strain": strain or "unknown",
        "media": media or "unknown",
        "angle": angle or "unknown",
    }


def _extract_strain_from_path(rel_path: Path) -> str:
    """Extract strain identifier from the relative path of a file in a ZIP.

    Looks for a folder named after a strain identifier.
    Expected structure: .../images/{strain}/image.jpg or .../{strain}/image.jpg
    Falls back to 'unknown-strain' if no meaningful folder found.
    """
    parts = rel_path.parts
    # Skip root-level entries like AGENTS.md, scripts/, images/
    skip_prefixes = {"images", "mycoai_batch", "mycoai_batch_template"}
    meaningful = [
        p for p in parts[:-1]  # exclude filename
        if p.lower() not in skip_prefixes and not p.startswith(".")
    ]
    if meaningful:
        return meaningful[-1]  # innermost folder = strain
    # Fallback: use parent folder if not root
    if len(parts) >= 2:
        return parts[-2]
    return "unknown-strain"
