from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SpeciesCreate(BaseModel):
    name: str
    description: str | None = None


class SpeciesUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class SpeciesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class SpeciesListResponse(BaseModel):
    items: list[SpeciesResponse]
    total: int
