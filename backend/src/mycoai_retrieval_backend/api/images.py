from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..core.dependencies import get_current_user
from ..schemas import ImageDetail, ImageUploadResponse, SegmentDetail
from ..services.stores import get_image_store, get_segment_store, new_id, utcnow

router = APIRouter()


@router.post("/upload", response_model=ImageUploadResponse, status_code=201)
async def upload_image(
    user: dict = Depends(get_current_user),
    image: UploadFile = File(...),
    strain: str = Form(...),
    media: str = Form(...),
    max_colonies: int | None = Form(None),
) -> dict:
    store = get_image_store()
    image_id = new_id()
    job_id = new_id()
    item = {
        "id": image_id,
        "strain_id": None,
        "strain": strain,
        "media": media,
        "max_colonies": max_colonies,
        "status": "pending_segmentation",
        "file_path": f"images/{image.filename or image_id}.png",
        "is_archived": False,
        "created_at": utcnow(),
    }
    store.put(item)
    return {
        "image_id": image_id,
        "strain": strain,
        "media": media,
        "status": "pending_segmentation",
        "job_id": job_id,
    }


@router.post("/batch", status_code=202)
async def batch_upload(user: dict = Depends(get_current_user)) -> dict:
    job_id = new_id()
    return {"job_id": job_id, "status": "processing"}


@router.get("/{image_id}", response_model=ImageDetail)
def get_image(image_id: str, user: dict = Depends(get_current_user)) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_image_store()
    image = store.get(image_id)
    if not image:
        raise NotFoundError(f"Image with id {image_id} not found")
    seg_store = get_segment_store()
    segments = [s for s in seg_store.list() if s.get("image_id") == image_id]
    return {
        "id": image["id"],
        "strain": image.get("strain", ""),
        "media": image.get("media", ""),
        "status": image.get("status", "pending_segmentation"),
        "segments": segments,
    }


@router.delete("/{image_id}", status_code=204)
def delete_image(image_id: str, user: dict = Depends(get_current_user)) -> None:
    from ..core.exceptions import NotFoundError

    store = get_image_store()
    image = store.get(image_id)
    if not image:
        raise NotFoundError(f"Image with id {image_id} not found")
    image["is_archived"] = True
    store.put(image)


@router.get("/{image_id}/segments", response_model=list[SegmentDetail])
def list_segments(image_id: str, user: dict = Depends(get_current_user)) -> list[dict]:
    seg_store = get_segment_store()
    return [s for s in seg_store.list() if s.get("image_id") == image_id]
