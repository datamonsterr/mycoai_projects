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
