from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .image_models import ImageResponse, SegmentPatchRequest
from .segmentation import ImageStore, SegmentationPipeline


def create_image_router(
    *,
    store: ImageStore,
    pipeline: SegmentationPipeline,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/images", tags=["images"])

    @router.post("", response_model=ImageResponse, status_code=201)
    async def upload_image(
        image: Annotated[UploadFile, File(...)],
        strain: Annotated[str, Form()] = "unknown-strain",
        media: Annotated[str, Form()] = "unknown-media",
        method: Annotated[str, Form()] = "kmeans",
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

        store.add(record)
        return ImageResponse.model_validate(record.model_dump())

    @router.get("/{image_id}", response_model=ImageResponse)
    def get_image(image_id: str) -> ImageResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        return ImageResponse.model_validate(record.model_dump())

    @router.patch("/{image_id}/segments", response_model=ImageResponse)
    def update_segments(
        image_id: str,
        patch: SegmentPatchRequest,
    ) -> ImageResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        updated = pipeline.update_segments(record, patch)
        store.add(updated)
        return ImageResponse.model_validate(updated.model_dump())

    @router.get("/{image_id}/segments/{segment_index}/crop")
    def get_crop(image_id: str, segment_index: int) -> FileResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        crop_path = record.artifact_dir / "segments" / f"segment_{segment_index}.jpg"
        if not crop_path.exists():
            raise HTTPException(status_code=404, detail="segment not found")
        return FileResponse(crop_path)

    @router.get("/{image_id}/pipeline")
    def get_pipeline(image_id: str, method: str = "kmeans") -> FileResponse:
        record = store.get(image_id)
        if record is None:
            raise HTTPException(status_code=404, detail="image not found")
        pipeline_path = record.artifact_dir / f"pipeline_{method}.jpg"
        if not pipeline_path.exists():
            raise HTTPException(status_code=404, detail="pipeline image not found")
        return FileResponse(pipeline_path)

    return router
