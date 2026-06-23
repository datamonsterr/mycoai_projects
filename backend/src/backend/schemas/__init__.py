from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from .auth import (  # noqa: F401
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


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


class ImageListItem(BaseModel):
    id: str
    strain_name: str
    species_id: str
    species_name: str
    media_id: str
    media_name: str
    file_path: str
    source_url: str = ""
    angle: str | None = None
    segments_count: int = 0
    data_update_status: str
    indexed_in_qdrant: bool = False
    is_archived: bool = False
    created_at: datetime


class ImageListResponse(BaseModel):
    items: list[ImageListItem]
    total: int


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


class ThresholdConfidence(BaseModel):
    formula: str = "gnorm_0_2"
    confidence: float = 0.0
    threshold: float = 0.12
    is_known: bool = True


class RetrievalResultsResponse(BaseModel):
    job_id: str
    status: str
    strain: str
    rankings: list[RetrievalRanking]
    threshold: ThresholdConfidence | None = None


from .species import (  # noqa: E402, F401
    SpeciesCreate,
    SpeciesListResponse,
    SpeciesResponse,
    SpeciesUpdate,
)

SpeciesCreateRequest = SpeciesCreate
SpeciesUpdateRequest = SpeciesUpdate

AuthLoginRequest = LoginRequest
AuthRefreshRequest = RefreshRequest
AuthRegisterRequest = RegisterRequest
TokenPair = TokenResponse
UserProfile = UserResponse


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


from .feedback import (  # noqa: E402, F401
    FeedbackBatchRequest,
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
)

FeedbackCreateRequest = FeedbackCreate


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


from .dashboard import (  # noqa: E402, F401
    DashboardStats,
    MediaDistributionItem,
    SpeciesDistributionItem,
)


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
