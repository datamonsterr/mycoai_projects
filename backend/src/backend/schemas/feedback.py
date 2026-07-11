from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    retrieval_result_id: UUID | None = None
    feedback_type: Literal["wrong_prediction", "issue", "contribution"]
    suggested_species: str | None = Field(default=None, min_length=1)
    description: str = Field(min_length=1)
    query_strain: str | None = None
    image_id: UUID | None = None
    predicted_species: str | None = None


class FeedbackUpdate(BaseModel):
    status: Literal["accepted", "rejected", "deferred"]
    review_note: str | None = None


class FeedbackResponse(BaseModel):
    id: str
    submitter_id: str
    reviewer_id: str | None = None
    source: str
    feedback_type: str
    query_strain: str | None = None
    result_id: str | None = None
    predicted_species: str | None = None
    suggested_species: str
    description: str
    status: str
    review_note: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None

    model_config = {"from_attributes": True}


class FeedbackBatchRequest(BaseModel):
    feedback_ids: list[str]
    status: Literal["accepted", "rejected", "deferred"]
    review_note: str | None = None
