"""
Image routes with DB persistence + file storage + segmentation.

POST /api/v1/images              − upload single image (segment + db)
POST /api/v1/images/upload       − alias for single image upload
GET  /api/v1/images/{id}         − get image detail from db
POST /api/v1/images/batch        − import batch from server folder
POST /api/v1/images/batch-upload − upload folder (multipart files + metadata)
POST /api/v1/images/batch-zip    − upload ZIP batch (extract + segment + db)
"""

import asyncio
import csv
import json
import logging
import shutil
import uuid
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from .core.dependencies import get_current_user, require_owner
from .database import get_db
from .image_models import (
    BatchImageStatus,
    BatchProgressResponse,
    BatchStrainStatus,
    BoundingBox,
    ImageRecord,
    ImageResponse,
    ProcessingProgress,
    SegmentPatchRequest,
)
from .image_models import Segment as SegModel
from .models import Image, Media, QdrantIndexState, Segment, Species, Strain
from .qdrant import delete_points, get_qdrant_client
from .repos.media import _normalize_media_name
from .schemas import ImageListItem, ImageListResponse
from .segmentation import ALLOWED_METHODS, SegmentationPipeline
from .segmentation import ImageStore as FileStore
from .services.feature_extraction import index_segment_to_qdrant
from .services.storage import (
    ObjectStorage,
    cleanup_source_artifact,
    storage_artifact_prefix,
    storage_candidates,
)

logger = logging.getLogger(__name__)
SEGMENT_CONCURRENCY_LIMIT = 2
_BATCH_PROGRESS: dict[str, BatchProgressResponse] = {}


class BatchImportRequest(BaseModel):
    source_dir: str
    method: str = "kmeans"


class AutoSegmentRequest(BaseModel):
    method: str = "kmeans"


def _progress(completed: int, total: int) -> ProcessingProgress:
    return ProcessingProgress(
        completed=completed,
        total=total,
        percent=round((completed / total) * 100) if total else 100,
    )


def _batch_progress(
    batch_id: str,
    batch_name: str,
    images: list[BatchImageStatus],
) -> BatchProgressResponse:
    total = len(images)
    uploaded = sum(
        img.status in {"uploaded", "segmented", "extracting", "indexed"}
        for img in images
    )
    segmented = sum(
        img.status in {"segmented", "extracting", "indexed"}
        for img in images
    )

    indexed = sum(img.status == "indexed" for img in images)
    failed = any(img.status == "failed" for img in images)
    done = (
        sum(img.status in {"segmented", "indexed", "failed"} for img in images)
        == total
    )
    strain_names = sorted({img.strain for img in images})
    strains = []
    for strain in strain_names:
        strain_images = [img for img in images if img.strain == strain]
        strain_total = len(strain_images)
        strain_segmented = sum(
            img.status in {"segmented", "extracting", "indexed"}
            for img in strain_images
        )
        strain_indexed = sum(img.status == "indexed" for img in strain_images)
        strains.append(
            BatchStrainStatus(
                strain=strain,
                confirmed=(
                    strain_total > 0
                    and not any(
                        img.status in {"uploaded", "segmented", "extracting"}
                        for img in strain_images
                    )
                ),
                upload=_progress(
                    sum(
                        img.status in {"uploaded", "segmented", "extracting", "indexed"}
                        for img in strain_images
                    ),
                    strain_total,
                ),
                segmentation=_progress(strain_segmented, strain_total),
                feature_extraction=_progress(strain_indexed, strain_total),
            )
        )
    status = "completed" if done else "processing"
    if failed and done:
        status = "completed_with_errors"
    return BatchProgressResponse(
        batch_id=batch_id,
        status=status,
        batch_name=batch_name,
        upload=_progress(uploaded, total),
        segmentation=_progress(segmented, total),
        feature_extraction=_progress(indexed, total),
        strains=strains,
        images=images,
    )


def _set_batch_progress(
    batch_id: str,
    batch_name: str,
    images: list[BatchImageStatus],
) -> BatchProgressResponse:
    progress = _batch_progress(batch_id, batch_name, images)
    _BATCH_PROGRESS[batch_id] = progress
    return progress


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
                    source_url = candidate.replace("http://minio:9000/", "/minio/")
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
            record = await asyncio.to_thread(
                pipeline.segment_upload,
                temp_path,
                strain=strain,
                media=media,
                method=method,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            logger.warning("segmentation failed for upload %s: %s", image.filename, exc)
            raise HTTPException(status_code=422, detail="segmentation failed") from exc
        finally:
            temp_path.unlink(missing_ok=True)

        species_obj = await _ensure_species(db, species)
        media_obj = await _ensure_media(db, media)
        strain_obj = await _ensure_strain(db, strain, species_obj.id)
        image_obj = await _create_image(db, record, strain_obj, species_obj, media_obj)

        # Re-fetch image with eagerly-loaded segments.
        result = await db.execute(
            select(Image)
            .options(selectinload(Image.segments))
            .where(Image.id == image_obj.id)
        )
        image_obj = result.scalar_one()

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

        # Persist segment updates (qdrant_point_id, qdrant_index_state) to DB
        await db.commit()

        record.image_id = str(image_obj.id)
        record.source_url = f"/api/v1/images/{record.image_id}/source"
        for seg_model in record.segments:
            seg_model.crop_url = (
                f"/api/v1/images/{record.image_id}"
                f"/segments/{seg_model.segment_index}/crop"
            )
            seg_model.pipeline_url = (
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
                cleanup_source_artifact(storage, record.artifact_dir)

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
        default_media: Annotated[str, Form()] = "Other media",
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
                cleanup_source_artifact(storage, record.artifact_dir)
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

    async def _run_batch_zip_job(
        *,
        batch_id: str,
        batch_name: str,
        work_dir: Path,
        jobs: list[tuple[Path, Path, str, str, str, str]],
        method: str,
        db_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        image_statuses = _BATCH_PROGRESS[batch_id].images
        by_filename = {image.filename: image for image in image_statuses}
        semaphore = asyncio.Semaphore(SEGMENT_CONCURRENCY_LIMIT)

        async def segment_one(job: tuple[Path, Path, str, str, str, str]):
            img_path, rel_path, strain, media_name, species, image_id = job
            try:
                async with semaphore:
                    status = by_filename[str(rel_path)]
                    status.status = "uploaded"
                    _set_batch_progress(batch_id, batch_name, image_statuses)
                    record = await asyncio.to_thread(
                        pipeline.segment_upload,
                        img_path,
                        strain=strain,
                        media=media_name,
                        method=method,
                        image_id=image_id,
                    )
                return rel_path, strain, media_name, species, image_id, record, None
            except Exception as exc:
                return rel_path, strain, media_name, species, image_id, None, str(exc)

        try:
            tasks = [asyncio.create_task(segment_one(job)) for job in jobs]
            async with db_factory() as db_session:
                existing_rows = await db_session.execute(
                    select(Strain.name, Species.name).join(
                        Species, Strain.species_id == Species.id
                    )
                )
                existing_species_by_strain = {
                    strain_name: species_name
                    for strain_name, species_name in existing_rows.all()
                    if species_name not in {"unknown", "unknown-species"}
                    and species_name.startswith("Penicillium ")
                }
                for task in asyncio.as_completed(tasks):
                    rel_path, strain, media_name, species, image_id, record, error = (
                        await task
                    )
                    status = by_filename[str(rel_path)]
                    if error or record is None:
                        status.status = "failed"
                        status.error = error or "segmentation failed"
                        _set_batch_progress(batch_id, batch_name, image_statuses)
                        continue
                    try:
                        resolved_species = existing_species_by_strain.get(
                            strain, species
                        )
                        species_obj = await _ensure_species(
                            db_session, resolved_species
                        )
                        media_obj = await _ensure_media(db_session, media_name)
                        strain_obj = await _ensure_strain(
                            db_session, strain, species_obj.id
                        )
                        image_obj = await _create_image(
                            db_session,
                            record,
                            strain_obj,
                            species_obj,
                            media_obj,
                            commit=False,
                        )
                        await db_session.commit()
                        status.image_id = str(image_obj.id)
                        status.source_url = f"/api/v1/images/{image_obj.id}/source"
                        status.status = "segmented"
                        status.segments = len(record.segments)
                        status.segment_urls = [
                            f"/api/v1/images/{image_obj.id}/segments/{seg.segment_index}/crop"
                            for seg in record.segments
                        ]
                        _set_batch_progress(batch_id, batch_name, image_statuses)
                    except Exception as exc:
                        await db_session.rollback()
                        status.status = "failed"
                        status.error = str(exc)
                    _set_batch_progress(batch_id, batch_name, image_statuses)
        finally:
            _set_batch_progress(batch_id, batch_name, image_statuses)
            shutil.rmtree(work_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Batch ZIP upload: accept a ZIP file, extract, segment, and persist
    # ------------------------------------------------------------------
    @router.post("/batch-zip", status_code=202)
    async def batch_zip_upload(
        zipfile_file: Annotated[UploadFile, File(alias="zipfile")],
        default_media: Annotated[str, Form()] = "Other media",
        default_species: Annotated[str, Form()] = "unknown-species",
        method: Annotated[str, Form()] = "yolo",
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict[str, Any]:
        if not zipfile_file.filename or not zipfile_file.filename.lower().endswith(
            ".zip"
        ):
            raise HTTPException(status_code=422, detail="Only .zip files are accepted")

        work_dir = Path(mkdtemp(prefix="batch_zip_"))
        zip_path = work_dir / "upload.zip"

        try:
            with zip_path.open("wb") as out:
                while chunk := await zipfile_file.read(1024 * 1024):
                    out.write(chunk)

            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(work_dir)

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
        except zipfile.BadZipFile:
            shutil.rmtree(work_dir, ignore_errors=True)
            raise HTTPException(
                status_code=422, detail="Invalid or corrupted ZIP file"
            ) from None

        batch_name = Path(zipfile_file.filename or "batch").stem
        batch_id = uuid.uuid4().hex
        image_statuses: list[BatchImageStatus] = []
        jobs: list[tuple[Path, Path, str, str, str, str]] = []

        strain_species_map: dict[str, str] = {}
        for csv_path in (
            Path("Dataset/strain_to_specy.csv"),
            Path("/app/Dataset/strain_to_specy.csv"),
        ):
            if csv_path.exists():
                with csv_path.open() as handle:
                    for row in csv.DictReader(handle):
                        strain_key = (row.get("Strain") or "").strip().upper()
                        species_val = (row.get("Species") or "").strip()
                        if strain_key and species_val:
                            strain_species_map[strain_key] = species_val
                break
        existing_rows = await db.execute(
            select(Strain.name, Species.name).join(
                Species, Strain.species_id == Species.id
            )
        )
        for strain_name, species_name in existing_rows.all():
            key = strain_name.strip().upper()
            if not key:
                continue
            if species_name in {"unknown", "unknown-species"}:
                continue
            if species_name.startswith("Penicillium "):
                strain_species_map[key] = species_name
        for img_path in image_files:
            rel_path = img_path.relative_to(work_dir)
            image_id = uuid.uuid4().hex
            path_parts = [p for p in rel_path.parts[:-1] if p]
            species, strain = _extract_species_and_strain_from_path(rel_path)
            meta = _parse_filename_metadata(img_path.name, str(rel_path))
            if strain == "unknown-strain":
                strain = meta.get("strain", strain)
            if species in {"unknown", "unknown-species"}:
                species = meta.get("species", default_species)
            if species in {"unknown", "unknown-species", default_species}:
                species = strain_species_map.get(strain.upper(), default_species)
            folder_media = next(
                (
                    _normalize_media_name(part)
                    for part in reversed(path_parts)
                    if _normalize_media_name(part)
                    in {"CREA", "CYA", "DG18", "MEA", "YES", "OA", "M40Y"}
                ),
                None,
            )
            media_name = _normalize_media_name(
                folder_media or meta.get("media", "") or default_media
            )
            if media_name in {"", "UNKNOWN"}:
                media_name = (
                    _normalize_media_name(default_media or "Other media")
                    or "OTHER MEDIA"
                )
            jobs.append((img_path, rel_path, strain, media_name, species, image_id))
            image_statuses.append(
                BatchImageStatus(
                    filename=str(rel_path),
                    strain=strain,
                    media=media_name,
                    species=species,
                    status="queued",
                    image_id=image_id,
                    source_url=None,
                )
            )

        progress = _set_batch_progress(batch_id, batch_name, image_statuses)
        db_factory = async_sessionmaker(
            bind=db.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        asyncio.create_task(
            _run_batch_zip_job(
                batch_id=batch_id,
                batch_name=batch_name,
                work_dir=work_dir,
                jobs=jobs,
                method=method,
                db_factory=db_factory,
            )
        )

        return {
            "status": progress.status,
            "batch_id": batch_id,
            "batch_name": batch_name,
            "total": len(image_statuses),
            "successful": 0,
            "failed": 0,
            "results": [],
            "errors": [],
            "progress": progress.model_dump(),
        }

    @router.get("/batches/{batch_id}/progress", response_model=BatchProgressResponse)
    async def get_batch_progress(
        batch_id: str,
        user=Depends(get_current_user),
    ) -> BatchProgressResponse:
        progress = _BATCH_PROGRESS.get(batch_id)
        if progress is None:
            raise HTTPException(status_code=404, detail="batch progress not found")
        return progress

    @router.post(
        "/batches/{batch_id}/strains/{strain}/confirm",
        response_model=BatchProgressResponse,
    )
    async def confirm_batch_strain(
        batch_id: str,
        strain: str,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> BatchProgressResponse:
        progress = _BATCH_PROGRESS.get(batch_id)
        if progress is None:
            raise HTTPException(status_code=404, detail="batch progress not found")

        target_images = [
            image
            for image in progress.images
            if image.strain == strain and image.status == "segmented"
        ]
        if not target_images:
            return progress

        for image_status in target_images:
            if not image_status.image_id:
                continue
            try:
                img_uuid = UUID(image_status.image_id)
            except ValueError:
                image_status.status = "failed"
                image_status.error = "invalid image id"
                continue

            result = await db.execute(
                select(Image)
                .options(
                    selectinload(Image.segments),
                    selectinload(Image.strain),
                    selectinload(Image.species),
                    selectinload(Image.media),
                )
                .where(Image.id == img_uuid)
            )
            img = result.scalar_one_or_none()
            if img is None:
                image_status.status = "failed"
                image_status.error = "image not found"
                continue

            image_status.status = "extracting"
            _BATCH_PROGRESS[batch_id] = _batch_progress(
                batch_id, progress.batch_name, progress.images
            )
            try:
                indexed_segments = await _reindex_image_segments(db, img, storage)
                await db.commit()
                total_segments = image_status.segments or len(img.segments)
                image_status.status = (
                    "indexed" if indexed_segments >= total_segments else "failed"
                )
                image_status.segments = total_segments
                image_status.segment_urls = image_status.segment_urls or [
                    f"/api/v1/images/{img.id}/segments/{seg.segment_index}/crop"
                    for seg in img.segments
                ]
                if image_status.status == "failed":
                    image_status.error = "not all segments indexed"
            except Exception as exc:
                await db.rollback()
                image_status.status = "indexed"
                image_status.error = str(exc)

        progress = _batch_progress(batch_id, progress.batch_name, progress.images)
        _BATCH_PROGRESS[batch_id] = progress
        return progress

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
        patch: SegmentPatchRequest,
        db=Depends(get_db),
        user=Depends(get_current_user),
    ) -> ImageResponse:
        record = store.get(image_id)
        if record is not None:
            updated = pipeline.update_segments(record, patch)
            store.add(updated)
            return ImageResponse.model_validate(updated.model_dump())

        img = await _get_image_for_update(db, image_id)
        record = _record_from_image(img, storage)
        updated = pipeline.update_segments(record, patch)
        _sync_record_to_db(img, updated)
        await _clear_segment_index_state(db, img.segments)
        img.data_update_status = "updated_requires_reindex"
        await db.commit()
        return ImageResponse.model_validate(updated.model_dump())

    @router.patch("/{image_id}/media")
    async def update_image_media(
        image_id: str,
        body: dict[str, str],
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict[str, str]:
        media_name = _normalize_media_name(body.get("media", ""))
        if not media_name:
            raise HTTPException(status_code=422, detail="media is required")
        img = await _get_image_for_update(db, image_id)
        media_obj = await _ensure_media(db, media_name)
        img.media_id = media_obj.id
        if img.media is not None:
            img.media = media_obj
        img.data_update_status = "updated_requires_reindex"
        await _clear_segment_index_state(db, img.segments)
        await db.commit()
        return {"image_id": str(img.id), "media": media_obj.name}

    @router.post("/{image_id}/reindex")
    async def reindex_image(
        image_id: str,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict[str, int | str]:
        img = await _get_image_for_update(db, image_id)
        indexed_segments = await _reindex_image_segments(db, img, storage)
        await db.commit()
        return {
            "image_id": str(img.id),
            "segments": len(img.segments),
            "indexed_segments": indexed_segments,
        }

    @router.post("/strains/{strain_id}/reindex")
    async def reindex_strain(
        strain_id: str,
        db=Depends(get_db),
        user=Depends(require_owner()),
    ) -> dict[str, int | str]:
        try:
            strain_uuid = UUID(strain_id)
        except ValueError as err:
            raise HTTPException(status_code=404, detail="strain not found") from err

        result = await db.execute(
            select(Image)
            .options(
                selectinload(Image.segments),
                selectinload(Image.strain),
                selectinload(Image.species),
                selectinload(Image.media),
            )
            .where(Image.strain_id == strain_uuid, Image.is_archived.is_(False))
        )
        images = list(result.scalars().all())
        if not images:
            raise HTTPException(status_code=404, detail="strain not found")

        indexed_segments = 0
        eligible_images = 0
        for img in images:
            if img.data_update_status != "updated_requires_reindex" and all(
                seg.qdrant_point_id is not None for seg in img.segments
            ):
                continue
            eligible_images += 1
            indexed_segments += await _reindex_image_segments(db, img, storage)
        await db.commit()
        return {
            "strain_id": strain_id,
            "images": eligible_images,
            "indexed_segments": indexed_segments,
        }

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
            # Run segmentation (CPU-bound cv2/sklearn in thread)
            record = await asyncio.to_thread(
                pipeline.segment_upload,
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
            # Delete associated qdrant_index_state rows first to avoid FK violation
            await db.execute(
                delete(QdrantIndexState).where(QdrantIndexState.segment_id == seg.id)
            )
            await db.delete(seg)
        await db.flush()

        # Create new segments (resolve to absolute crop_path so cv2 can re-read them)
        from .config import get_storage_settings as _gss

        _root = Path(_gss().upload_root)
        if not _root.is_absolute():
            _root = (Path.cwd() / _root).resolve()
        for seg_model in record.segments:
            segment = Segment(
                image_id=img.id,
                segment_index=seg_model.segment_index,
                crop_path=str(
                    (
                        _root
                        / record.artifact_dir
                        / "segments"
                        / f"segment_{seg_model.segment_index}.jpg"
                    ).resolve()
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

        # Reload image with freshly committed segments (avoid lazy-load + stale IDs)
        result2 = await db.execute(
            select(Image)
            .options(
                selectinload(Image.segments),
                selectinload(Image.strain),
                selectinload(Image.species),
                selectinload(Image.media),
            )
            .where(Image.id == img.id)
        )
        img_reloaded = result2.scalar_one_or_none()
        if img_reloaded:
            strain_name = img_reloaded.strain.name if img_reloaded.strain else "unknown"
            species_name = (
                img_reloaded.species.name if img_reloaded.species else "unknown"
            )
            media_name = img_reloaded.media.name if img_reloaded.media else "unknown"
            for seg in img_reloaded.segments:
                if seg.qdrant_point_id is None:
                    try:
                        await index_segment_to_qdrant(
                            db,
                            seg,
                            img_reloaded,
                            strain_name=strain_name,
                            species_name=species_name,
                            media_name=media_name,
                            storage=storage,
                        )
                    except Exception as exc:
                        logger.warning(
                            "Qdrant index failed for segment %s: %s", seg.id, exc
                        )
            await db.commit()

        record.image_id = str(img.id)
        record.source_url = f"/api/v1/images/{record.image_id}/source"
        for seg in record.segments:
            seg.crop_url = (
                f"/api/v1/images/{record.image_id}/segments/{seg.segment_index}/crop"
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
            select(Image)
            .options(selectinload(Image.segments))
            .where(Image.id == img_uuid)
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
    @router.get("/{image_id}/segments/{segment_index}/crop", response_model=None)
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

        result = await db.execute(select(Image).where(Image.id == img_uuid))
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
        candidate_keys = [
            f"{artifact_dir}/{filename}",
            str(Path(*artifact_dir.parts[-4:]) / filename),
            str(Path(*artifact_dir.parts[-3:]) / filename),
        ]
        for key in dict.fromkeys(candidate_keys):
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


async def _get_image_for_update(db: AsyncSession, image_id: str) -> Image:
    try:
        img_uuid = UUID(image_id)
    except ValueError as err:
        raise HTTPException(status_code=404, detail="image not found") from err

    result = await db.execute(
        select(Image)
        .options(
            selectinload(Image.segments).selectinload(Segment.qdrant_index_state),
            selectinload(Image.strain),
            selectinload(Image.species),
            selectinload(Image.media),
        )
        .where(Image.id == img_uuid, Image.is_archived.is_(False))
    )
    img = result.scalar_one_or_none()
    if img is None:
        raise HTTPException(status_code=404, detail="image not found")
    return img


def _record_from_image(img: Image, storage: ObjectStorage | None) -> ImageRecord:
    segments = [
        SegModel(
            segment_id=f"{img.id}:{seg.segment_index}",
            segment_index=seg.segment_index,
            bbox=BoundingBox(x=seg.bbox_x, y=seg.bbox_y, w=seg.bbox_w, h=seg.bbox_h),
            crop_url=f"/api/v1/images/{img.id}/segments/{seg.segment_index}/crop",
            pipeline_url=f"/api/v1/images/{img.id}/pipeline?method={seg.segmentation_method}",
        )
        for seg in img.segments
    ]
    return ImageRecord(
        image_id=str(img.id),
        source_path=Path(img.file_path),
        artifact_dir=Path(img.file_path).parent,
        source_url=(
            f"/api/v1/images/{img.id}/source"
            if storage
            else f"/static/{img.strain.name}/{img.media.name}/{img.id}/source.jpg"
        ),
        segments=segments,
        segmentation_method=(
            img.segments[0].segmentation_method if img.segments else "kmeans"
        ),
    )


async def _clear_segment_index_state(db: AsyncSession, segments: list[Segment]) -> None:
    points_by_collection: dict[str, list[int]] = {}
    for seg in segments:
        state = seg.qdrant_index_state
        if state is not None:
            points_by_collection.setdefault(state.collection_name, []).append(
                state.qdrant_point_id.int
            )
            await db.delete(state)
            seg.qdrant_index_state = None
        elif seg.qdrant_point_id is not None:
            points_by_collection.setdefault("", []).append(seg.qdrant_point_id.int)
        seg.qdrant_point_id = None
    if points_by_collection:
        qdrant = get_qdrant_client()
        for collection_name, point_ids in points_by_collection.items():
            delete_points(qdrant, point_ids, collection_name=collection_name or None)
    await db.flush()


def _sync_record_to_db(img: Image, record: ImageRecord) -> None:
    artifact_dir = storage_artifact_prefix(
        strain=img.strain.name if img.strain else "unknown",
        media=img.media.name if img.media else "unknown",
        image_id=img.id,
    )

    by_index = {seg.segment_index: seg for seg in img.segments}
    for seg_model in record.segments:
        seg = by_index.get(seg_model.segment_index)
        if seg is None:
            continue
        seg.bbox_x = seg_model.bbox.x
        seg.bbox_y = seg_model.bbox.y
        seg.bbox_w = seg_model.bbox.w
        seg.bbox_h = seg_model.bbox.h
        seg.crop_path = str(
            artifact_dir / "segments" / f"segment_{seg.segment_index}.jpg"
        )


async def _reindex_image_segments(
    db: AsyncSession,
    img: Image,
    storage: ObjectStorage | None,
) -> int:
    strain_name = img.strain.name if img.strain else "unknown"
    species_name = img.species.name if img.species else "unknown"
    media_name = img.media.name if img.media else "unknown"
    indexed_segments = 0
    for seg in img.segments:
        result = await index_segment_to_qdrant(
            db,
            seg,
            img,
            strain_name=strain_name,
            species_name=species_name,
            media_name=media_name,
            storage=storage,
        )
        if result.get("status") == "indexed":
            indexed_segments += 1
    img.data_update_status = "current"
    return indexed_segments


def _read_source_from_storage(
    storage: ObjectStorage, img: Image, source_path: Path
) -> bytes | None:
    """Read source image bytes from object storage."""
    from .config import get_storage_settings

    upload_root = Path(get_storage_settings().upload_root)
    if not upload_root.is_absolute():
        upload_root = (Path.cwd() / upload_root).resolve()

    for key in storage_candidates(
        source_path,
        upload_root=upload_root,
        strain=img.strain.name if img.strain else None,
        media=img.media.name if img.media else None,
        image_id=img.id,
    ):
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
    upload_root: Path | None = None,
    *,
    commit: bool = True,
) -> Image:
    from .config import get_storage_settings

    settings = get_storage_settings()
    root = upload_root or Path(settings.upload_root)
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()

    source_path = record.source_path
    if settings.backend == "s3":
        artifact_dir = storage_artifact_prefix(
            strain=strain_obj.name,
            media=media_obj.name,
            image_id=record.image_id,
        )
        source_path = artifact_dir / "source.jpg"
        prepared_path = artifact_dir / "prepared.jpg"
        pipeline_path = artifact_dir / f"pipeline_{record.segmentation_method}.jpg"
    else:
        if not source_path.is_absolute():
            source_path = (root / source_path).resolve()
        prepared_path = (root / record.artifact_dir / "prepared.jpg").resolve()
        pipeline_path = (
            root / record.artifact_dir / f"pipeline_{record.segmentation_method}.jpg"
        ).resolve()

    img = Image(
        strain_id=strain_obj.id,
        species_id=species_obj.id,
        media_id=media_obj.id,
        file_path=str(source_path),
        prepared_path=str(prepared_path),
        pipeline_path=str(pipeline_path),
        data_update_status="current",
    )
    db.add(img)
    await db.flush()

    for seg in record.segments:
        crop_path = (
            artifact_dir / "segments" / f"segment_{seg.segment_index}.jpg"
            if settings.backend == "s3"
            else (
                root
                / record.artifact_dir
                / "segments"
                / f"segment_{seg.segment_index}.jpg"
            ).resolve()
        )
        segment = Segment(
            image_id=img.id,
            segment_index=seg.segment_index,
            crop_path=str(crop_path),
            bbox_x=seg.bbox.x,
            bbox_y=seg.bbox.y,
            bbox_w=seg.bbox.w,
            bbox_h=seg.bbox.h,
            segmentation_method=record.segmentation_method,
        )
        db.add(segment)

    if commit:
        await db.commit()
    else:
        await db.flush()
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

    structured = re.match(
        r"^(dto\s+\d+[\-a-z0-9]+|cbs\s+[\d_/]+|ibt\s+\d+|nrrl\s+\d+|t\d+)[_\s-]+(cya30|cyas|cya|mea|yes|dg18|crea|oa|m40y)[_\s-]+(ob|rev)(?:[_\s-].*)?$",
        lower,
        re.IGNORECASE,
    )
    if structured:
        strain = structured.group(1).upper()
        raw_media = structured.group(2).upper()
        media = "CYA" if raw_media in ("CYA30", "CYAS") else raw_media
        angle = structured.group(3).lower()
        return {
            "species": "unknown",
            "strain": strain,
            "media": media,
            "angle": angle,
        }

    rest = lower

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
        # Strategy 2: "MEDIA ANGLE" separated by space/underscore/hyphen
        m_angle = re.search(
            r"(?:^|[\s_-])(cya30|cyas|cya|mea|yes|dg18|crea|oa|m40y)[\s_-]+(ob|rev)(?:$|[\s_-])",
            lower,
        )
        if m_angle:
            raw_media = m_angle.group(1).upper()
            media = "CYA" if raw_media in ("CYA30", "CYAS") else raw_media
            angle = m_angle.group(2)
            rest = lower[: m_angle.start()].strip()

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
    if not species:
        species = "unknown"

    # Fallback: extract species/strain from folder path (DTO folder format)
    if species == "unknown" and rel_path:
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
            p
            for p in parts[:-1]
            if p not in alpha_patterns
            and not p.lower().endswith((".jpg", ".jpeg", ".png", ".jpe"))
        ]
        species_candidates = [
            p
            for p in meaningful
            if p.lower().startswith("penicillium") or " " in p
        ]
        if species_candidates:
            species = species_candidates[-1]
        if strain == "unknown" and meaningful:
            strain = meaningful[-1]

    return {
        "species": species or "unknown",
        "strain": strain or "unknown",
        "media": media or "unknown",
        "angle": angle or "unknown",
    }


def _extract_species_and_strain_from_path(rel_path: Path) -> tuple[str, str]:
    parts = [p for p in rel_path.parts[:-1] if p and not p.startswith(".")]
    skip_prefixes = {"images", "mycoai_batch", "mycoai_batch_template"}
    media_names = {"CREA", "CYA30", "CYAS", "CYA", "DG18", "MEA", "YES", "OA", "M40Y"}
    meaningful = [
        p
        for p in parts
        if p.lower() not in skip_prefixes and p.upper() not in media_names
    ]
    if len(meaningful) >= 2:
        return meaningful[0], meaningful[1]
    if len(meaningful) == 1:
        return "unknown-species", meaningful[0]
    return "unknown-species", "unknown-strain"


def _extract_strain_from_path(rel_path: Path) -> str:
    return _extract_species_and_strain_from_path(rel_path)[1]
