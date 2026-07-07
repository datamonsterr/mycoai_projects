from pathlib import Path

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(gt=0)
    h: int = Field(gt=0)


class Segment(BaseModel):
    segment_id: str
    segment_index: int = Field(ge=0)
    bbox: BoundingBox
    crop_url: str
    pipeline_url: str


class ImageRecord(BaseModel):
    image_id: str
    source_path: Path
    artifact_dir: Path
    source_url: str
    segments: list[Segment]
    segmentation_method: str


class ImageResponse(BaseModel):
    image_id: str
    source_url: str
    segments: list[Segment]
    segmentation_method: str


class SegmentPatch(BaseModel):
    segment_index: int = Field(ge=0)
    bbox: BoundingBox


class SegmentPatchRequest(BaseModel):
    segments: list[SegmentPatch] = Field(default_factory=list)
    deleted_segments: list[int] = Field(default_factory=list)


class ProcessingProgress(BaseModel):
    completed: int = Field(ge=0)
    total: int = Field(ge=0)
    percent: int = Field(ge=0, le=100)


class BatchImageStatus(BaseModel):
    filename: str
    strain: str
    media: str
    species: str
    status: str
    image_id: str | None = None
    segments: int = 0
    error: str | None = None
    source_url: str | None = None


class BatchStrainStatus(BaseModel):
    strain: str
    confirmed: bool = False
    upload: ProcessingProgress
    segmentation: ProcessingProgress
    feature_extraction: ProcessingProgress


class BatchProgressResponse(BaseModel):
    batch_id: str
    status: str
    batch_name: str
    upload: ProcessingProgress
    segmentation: ProcessingProgress
    feature_extraction: ProcessingProgress
    strains: list[BatchStrainStatus]
    images: list[BatchImageStatus]
