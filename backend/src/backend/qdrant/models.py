from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


@dataclass
class VectorSpec:
    name: str
    dimension: int


class NeighborResult(BaseModel):
    image_id: str | None = None
    score: float = 0.0
    distance: float = 1.0
    strain: str | None = None
    media: str | None = None
    angle: str | None = None
    specy: str | None = None
    parent_id: str | None = None
    segment_index: int | None = None
    bbox: dict[str, Any] | None = None
    extractor: str | None = None
    segment_path: str | None = None


class FilterSpec(BaseModel):
    media: str | None = None
    media_strategy: str | None = None
    exclude_media: str | None = None
    exclude_strain: str | None = None
    angle: str | None = None
    strain: str | None = None
    specy: str | None = None
    parent_id: str | None = None
    exclude_parent_id: str | None = None
    exclude_ids: list[int] | None = None


class QueryByImageRequest(BaseModel):
    image_path: str | None = None
    image_vector: list[float] | None = None
    feature_type: str | None = None
    k: int = Field(default=11, ge=1, le=100)
    filter_spec: FilterSpec | None = None


class QueryByIdRequest(BaseModel):
    point_id: int
    feature_type: str | None = None
    k: int = Field(default=11, ge=1, le=100)
    filter_spec: FilterSpec | None = None
    exclude_self: bool = True
    exclude_siblings: bool = True


class PointUpsertRequest(BaseModel):
    point_id: int
    vectors: dict[str, list[float]]
    payload: dict[str, Any]


class QueryResult(BaseModel):
    neighbors: list[NeighborResult]
    total: int


class AggregationResult(BaseModel):
    top_species: str
    top_score: float
    ranking: list[RankedEntry]

    class RankedEntry(BaseModel):
        species: str
        score: float


class AggregationRequest(BaseModel):
    neighbors: list[list[NeighborResult]]
    strain_to_specy: dict[str, str]
    k: int = 11
    strategy: str = "weighted"


class CollectionStats(BaseModel):
    total_points: int | None = None
    vector_types: list[str] = Field(default_factory=list)
    vector_dimensions: dict[str, int] = Field(default_factory=dict)
    collection_name: str = ""
    status: str = "ok"
