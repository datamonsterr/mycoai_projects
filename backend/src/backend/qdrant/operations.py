from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, cast

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointsSelector
from qdrant_client.models import PointStruct

from ..config import get_qdrant_settings
from .filters import build_filter
from .models import FilterSpec, NeighborResult, PointUpsertRequest, QueryResult


def _point_payload(point: Any) -> dict[str, Any]:
    return dict(getattr(point, "payload", {}) or {})


def _neighbor_from_point(point: Any) -> NeighborResult:
    payload = _point_payload(point)
    score = float(getattr(point, "score", 0.0) or 0.0)
    return NeighborResult(
        image_id=payload.get("image_id"),
        score=score,
        distance=1.0 - score,
        strain=payload.get("strain"),
        environment=payload.get("environment"),
        angle=payload.get("angle"),
        specy=payload.get("specy") or payload.get("species"),
        parent_id=payload.get("parent_id") or payload.get("parent_item_id"),
        segment_index=payload.get("segment_index"),
        bbox=payload.get("bbox"),
        extractor=payload.get("extractor"),
    )


def _points_from_response(response: Any) -> list[Any]:
    points = getattr(response, "points", response)
    return list(points)


def query_points_by_image(
    client: QdrantClient,
    image_vector: list[float],
    feature_type: str | None = None,
    k: int = 11,
    filter_spec: FilterSpec | None = None,
    collection_name: str | None = None,
) -> QueryResult:
    settings = get_qdrant_settings()
    collection = collection_name or settings.collection_name
    vector_name = feature_type or settings.default_vector_name
    response = client.query_points(
        collection_name=collection,
        query=image_vector,
        using=vector_name,
        query_filter=build_filter(filter_spec),
        limit=k,
        with_payload=True,
    )
    points = _points_from_response(response)
    neighbors = [_neighbor_from_point(point) for point in points[:k]]
    return QueryResult(neighbors=neighbors, total=len(neighbors))


def query_points_by_id(
    client: QdrantClient,
    point_id: int,
    feature_type: str | None = None,
    k: int = 11,
    filter_spec: FilterSpec | None = None,
    exclude_self: bool = True,
    exclude_siblings: bool = True,
    collection_name: str | None = None,
) -> QueryResult:
    settings = get_qdrant_settings()
    collection = collection_name or settings.collection_name
    vector_name = feature_type or settings.default_vector_name
    records = client.retrieve(
        collection_name=collection,
        ids=[point_id],
        with_vectors=True,
        with_payload=True,
    )
    points = list(records)
    if not points:
        raise ValueError(f"Point {point_id} not found")
    query_point = points[0]
    query_vectors = cast(dict[str, list[float]], query_point.vector)
    query_vector = query_vectors.get(vector_name)
    if query_vector is None:
        available = list(query_vectors.keys())
        raise ValueError(
            f"Feature type '{vector_name}' not found. Available types: {available}"
        )
    local_filter = filter_spec.model_copy(deep=True) if filter_spec else FilterSpec()
    if exclude_siblings:
        payload = _point_payload(query_point)
        parent_id = payload.get("parent_id") or payload.get("parent_item_id")
        if parent_id is not None:
            local_filter.parent_id = str(parent_id)
            local_filter.exclude_ids = (local_filter.exclude_ids or []) + [point_id]
    if exclude_self:
        local_filter.exclude_ids = (local_filter.exclude_ids or []) + [point_id]
    response = client.query_points(
        collection_name=collection,
        query=query_vector,
        using=vector_name,
        query_filter=build_filter(local_filter),
        limit=k + 1,
        with_payload=True,
    )
    points = _points_from_response(response)
    neighbors: list[NeighborResult] = []
    for point in points:
        if exclude_self and getattr(point, "id", None) == point_id:
            continue
        neighbors.append(_neighbor_from_point(point))
        if len(neighbors) >= k:
            break
    return QueryResult(neighbors=neighbors, total=len(neighbors))


def upsert_points(
    client: QdrantClient,
    points: Iterable[PointUpsertRequest],
    collection_name: str | None = None,
) -> int:
    settings = get_qdrant_settings()
    collection = collection_name or settings.collection_name
    structs = [
        PointStruct(
            id=point.point_id,
            vector=cast(dict[str, Any], point.vectors),
            payload=point.payload,
        )
        for point in points
    ]
    if not structs:
        return 0
    client.upsert(collection_name=collection, points=structs)
    return len(structs)


def delete_points(
    client: QdrantClient,
    point_ids: Sequence[int],
    collection_name: str | None = None,
) -> int:
    settings = get_qdrant_settings()
    collection = collection_name or settings.collection_name
    if not point_ids:
        return 0
    client.delete(
        collection_name=collection,
        points_selector=cast(PointsSelector, list(point_ids)),
    )
    return len(point_ids)
