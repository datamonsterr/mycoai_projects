from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..qdrant import (
    AggregationRequest,
    AggregationResult,
    CollectionStats,
    PointUpsertRequest,
    QueryByIdRequest,
    QueryByImageRequest,
    QueryResult,
    aggregate_predictions,
    get_collection_stats,
    get_qdrant_client,
    query_points_by_id,
    query_points_by_image,
    upsert_points,
)

router = APIRouter(prefix="/api", tags=["qdrant"])


@router.get("/collections/stats", response_model=CollectionStats)
def stats_endpoint() -> CollectionStats:
    client = get_qdrant_client()
    try:
        return get_collection_stats(client)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Qdrant unavailable: {exc}"
        ) from exc


@router.get("/collections/environments", response_model=list[str])
def environments_endpoint() -> list[str]:
    from ..qdrant.collections import list_environments

    client = get_qdrant_client()
    try:
        return list_environments(client)
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Qdrant unavailable: {exc}"
        ) from exc


@router.post("/search/by-image", response_model=QueryResult)
def search_by_image(request: QueryByImageRequest) -> QueryResult:
    if request.image_vector is None:
        raise HTTPException(status_code=400, detail="image_vector is required")
    client = get_qdrant_client()
    try:
        return query_points_by_image(
            client=client,
            image_vector=request.image_vector,
            feature_type=request.feature_type,
            k=request.k,
            filter_spec=request.filter_spec,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Qdrant query failed: {exc}"
        ) from exc


@router.post("/search/by-id", response_model=QueryResult)
def search_by_id(request: QueryByIdRequest) -> QueryResult:
    client = get_qdrant_client()
    try:
        return query_points_by_id(
            client=client,
            point_id=request.point_id,
            feature_type=request.feature_type,
            k=request.k,
            filter_spec=request.filter_spec,
            exclude_self=request.exclude_self,
            exclude_siblings=request.exclude_siblings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Qdrant query failed: {exc}"
        ) from exc


@router.post("/index/upsert", response_model=dict[str, int])
def index_upsert(points: list[PointUpsertRequest]) -> dict[str, int]:
    client = get_qdrant_client()
    try:
        count = upsert_points(client, points)
        return {"upserted": count}
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Qdrant upsert failed: {exc}"
        ) from exc


@router.post("/aggregate", response_model=AggregationResult)
def aggregate_endpoint(request: AggregationRequest) -> AggregationResult:
    try:
        raw_results = [
            {"neighbors": [n.model_dump() for n in group]}
            for group in request.neighbors
        ]
        return aggregate_predictions(
            raw_results=raw_results,
            strain_to_specy=request.strain_to_specy,
            k=request.k,
            strategy=request.strategy,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
