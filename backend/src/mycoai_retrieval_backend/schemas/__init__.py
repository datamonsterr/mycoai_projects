from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class AuthRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class AuthLogoutRequest(BaseModel):
    refresh_token: str


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Literal["user", "owner"]
    is_active: bool = True
    created_at: datetime


class ImageUploadResponse(BaseModel):
    image_id: str
    strain: str
    media: str
    status: str
    job_id: str


class ImageDetail(BaseModel):
    id: str
    strain: str
    media: str
    status: str
    segments: list[dict[str, object]] = Field(default_factory=list)


class SegmentDetail(BaseModel):
    id: str
    image_id: str
    segment_index: int
    crop_path: str
    bbox_x: int
    bbox_y: int
    bbox_w: int
    bbox_h: int
    segmentation_method: str


class RetrievalQueryRequest(BaseModel):
    image_id: str
    k: int = Field(default=5, ge=1)
    aggregation: str
    environment_strategy: str


class RetrievalJobResponse(BaseModel):
    job_id: str
    status: str
    estimated_seconds: int


class RetrievalNeighbor(BaseModel):
    strain: str
    species: str
    similarity: float
    media: str
    image_thumbnail_url: str


class RetrievalRanking(BaseModel):
    rank: int
    species: str
    score: float
    neighbors: list[RetrievalNeighbor]


class RetrievalResultsResponse(BaseModel):
    job_id: str
    status: str
    strain: str
    rankings: list[RetrievalRanking]


class SpeciesItem(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_archived: bool = False
    count: int = 0


class SpeciesCreateRequest(BaseModel):
    name: str
    description: str | None = None


class SpeciesUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class StrainItem(BaseModel):
    id: str
    name: str
    species_id: str
    source: str
    is_archived: bool = False
    images: list[str] = Field(default_factory=list)


class StrainCreateRequest(BaseModel):
    name: str
    species_id: str
    source: str = "user_upload"
    images: list[str] = Field(default_factory=list)


class FeedbackCreateRequest(BaseModel):
    source: str
    query_strain: str | None = None
    result_id: str | None = None
    image_id: str | None = None
    predicted_species: str | None = None
    suggested_species: str
    description: str


class FeedbackItem(BaseModel):
    id: str
    submitter_id: str
    reviewer_id: str | None = None
    source: str
    status: str
    suggested_species: str
    description: str


class FeedbackUpdateRequest(BaseModel):
    status: str
    review_note: str | None = None


class FeedbackBatchRequest(BaseModel):
    ids: list[str]
    status: str


class TrainingStatus(BaseModel):
    model_name: str
    version: str
    status: str
    deployed_at: datetime | None = None


class TrainingJobItem(BaseModel):
    id: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None


class TrainingTriggerRequest(BaseModel):
    reason: str | None = None


class TrainingDeployRequest(BaseModel):
    force: bool = False


class DashboardStats(BaseModel):
    species_count: int
    strains_count: int
    images_count: int


class ChartPoint(BaseModel):
    label: str
    value: int


class QdrantStatus(BaseModel):
    learned: int
    unlearned: int


class AdminUserItem(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    is_active: bool


class AdminRoleUpdateRequest(BaseModel):
    role: str


class ProblemDetails(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: list[dict[str, str]] | None = None
