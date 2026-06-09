from __future__ import annotations

import io
import zipfile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.dependencies import CurrentOwner
from ..database import get_db
from ..models import Image, Segment, Species

router = APIRouter()


def _yolo_bbox(seg: Segment, img_w: int = 640, img_h: int = 480) -> tuple[float, float, float, float]:
    """Convert absolute bbox to YOLO normalized format: x_center, y_center, width, height."""
    x_center = (seg.bbox_x + seg.bbox_w / 2) / img_w
    y_center = (seg.bbox_y + seg.bbox_h / 2) / img_h
    width = seg.bbox_w / img_w
    height = seg.bbox_h / img_h
    return (x_center, y_center, width, height)


@router.get("/export/yolo")
async def export_yolo(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    species_id: Annotated[str | None, Query()] = None,
    media_id: Annotated[str | None, Query()] = None,
    status: Annotated[str | None, Query()] = None,
) -> StreamingResponse:
    # Build query for active images with segments
    stmt = (
        select(Image)
        .options(selectinload(Image.segments), selectinload(Image.species))
        .where(Image.is_archived.is_(False))
    )

    # Exclude archived by default unless status explicitly includes them
    if status:
        stmt = stmt.where(Image.data_update_status == status)
    else:
        stmt = stmt.where(Image.data_update_status != "archived")

    if species_id:
        stmt = stmt.where(Image.species_id == UUID(species_id))
    if media_id:
        stmt = stmt.where(Image.media_id == UUID(media_id))

    result = await db.execute(stmt)
    images = result.unique().scalars().all()

    # Build species -> class index mapping
    species_set: dict[str, int] = {}
    for img in images:
        if img.species and img.species.name not in species_set:
            species_set[img.species.name] = len(species_set)

    # Build zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write classes.txt
        class_lines = [
            name for name, _ in sorted(species_set.items(), key=lambda x: x[1])
        ]
        zf.writestr("classes.txt", "\n".join(class_lines))

        for img in images:
            if not img.segments:
                continue

            # YOLO label file
            label_lines: list[str] = []
            species_name = img.species.name if img.species else "unknown"
            class_idx = species_set.get(species_name, -1)
            if class_idx < 0:
                continue

            for seg in img.segments:
                x_c, y_c, w, h = _yolo_bbox(seg)
                label_lines.append(f"{class_idx} {x_c:.6f} {y_c:.6f} {w:.6f} {h:.6f}")

            image_stem = img.file_path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
            zf.writestr(f"labels/{image_stem}.txt", "\n".join(label_lines))

            # Note: actual image binary not written (filesystem path only).
            # For a real implementation, read image bytes from storage.
            # Placeholder: write empty file with comment.
            zf.writestr(
                f"images/{image_stem}.txt",
                f"# Image: {img.file_path}\n# Strain: {img.strain_id}\n",
            )

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=mycoai_dataset_yolo.zip",
        },
    )
