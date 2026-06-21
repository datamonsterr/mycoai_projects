from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class StrainCreate(BaseModel):
    name: str
    species_id: UUID
    source: str = "user_upload"


class StrainUpdate(BaseModel):
    name: str | None = None
    species_id: UUID | None = None
    source: str | None = None


class ImageBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    file_path: str
    angle: str | None = None
    media_id: UUID
    data_update_status: str


class StrainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    species_id: UUID
    source: str
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    images: list[ImageBrief] = []


class StrainListResponse(BaseModel):
    items: list[StrainResponse]
    total: int
