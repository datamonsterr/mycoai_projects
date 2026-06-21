from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    scope: Literal["changed", "full_active"] = "changed"


class ReindexStatus(BaseModel):
    status: str = "current"
    items_updated: int = 0
    items_archived: int = 0
    feedback_accepted: int = 0
    contributions_accepted: int = 0


class RetrainingCounter(BaseModel):
    images_added: int = 0
    bbox_corrections: int = 0
    items_archived: int = 0
    species_added: int = 0
    last_reset_at: str | None = None


class RetrainingStatus(BaseModel):
    counter: RetrainingCounter = Field(default_factory=RetrainingCounter)
    threshold: int = 20
    warning_active: bool = False
    last_training_completed_at: str | None = None


class IndexStatusResponse(BaseModel):
    reindex: ReindexStatus = Field(default_factory=ReindexStatus)
    retraining: RetrainingStatus = Field(default_factory=RetrainingStatus)
    current_model_version: str = ""
