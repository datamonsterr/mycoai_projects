from dataclasses import dataclass
from datetime import datetime

from .base import BaseModel


@dataclass
class Species(BaseModel):
    name: str = ""
    description: str = ""


@dataclass
class Strain(BaseModel):
    name: str = ""
    species_id: str = ""
    isolation_source: str = ""


@dataclass
class Image(BaseModel):
    filename: str = ""
    status: str = "pending"
    strain_id: str | None = None


@dataclass
class Feedback(BaseModel):
    image_id: str = ""
    label: str = ""
    reviewer_id: str = ""


@dataclass
class TrainingJob(BaseModel):
    status: str = "queued"
    reason: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
