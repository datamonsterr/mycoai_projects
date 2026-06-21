from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MediaCreate(BaseModel):
    name: str
    description: str | None = None


class MediaUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class MediaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class MediaListResponse(BaseModel):
    items: list[MediaResponse]
    total: int
