"""Retrieval service — delegates to Qdrant-based species retrieval pipeline.

Default configuration (research-verified):
  - Extractor: EfficientNetB1_finetuned
  - Media strategy: same_media (E1 — query only same growth medium)
  - Aggregation: freq_strength
  - K: 11 (from threshold experiment default)

Allows per-query overrides for extractor, K, aggregation, and media strategy.
"""

from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient

from ..config import get_qdrant_settings
from ..qdrant.aggregation import aggregate_predictions
from ..qdrant.models import FilterSpec, NeighborResult, QueryResult
from ..qdrant.operations import query_points_by_id


def _neighbor_to_raw(
    neighbor: NeighborResult,
    strain_map: dict[str, str],
) -> dict[str, Any]:
    specy = neighbor.specy
    if not specy or specy == "unknown":
        specy = strain_map.get(neighbor.strain or "", "unknown")
    return {
        "specy": specy,
        "score": neighbor.score,
        "strain": neighbor.strain,
        "extractor": neighbor.extractor or "default",
        "media": neighbor.media,
        "image_id": neighbor.image_id,
    }


async def retrieve_by_point_id(
    qdrant: QdrantClient,
    collection: str,
    point_id: int,
    k: int = 11,
    media: str | None = None,
    exclude_strain: str | None = None,
    vector_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[NeighborResult]]:
    """Query Qdrant by existing point ID, return raw results and all neighbors."""
    settings = get_qdrant_settings()
    filter_spec = FilterSpec()
    if media is not None:
        filter_spec.media = media
    if exclude_strain is not None:
        filter_spec.exclude_strain = exclude_strain

    result: QueryResult = query_points_by_id(
        qdrant,
        point_id,
        feature_type=vector_name or settings.default_vector_name,
        k=k,
        filter_spec=filter_spec,
        exclude_self=True,
        exclude_siblings=True,
        collection_name=collection,
    )

    strain_map: dict[str, str] = {}
    all_neighbors: list[NeighborResult] = []
    raw: list[dict[str, Any]] = []

    seg_neighbors: list[dict[str, Any]] = []
    for neighbor in result.neighbors:
        strain_map[neighbor.strain or ""] = (
            neighbor.specy or neighbor.strain or "unknown"
        )
        raw_entry = _neighbor_to_raw(neighbor, strain_map)
        seg_neighbors.append(raw_entry)
        all_neighbors.append(neighbor)

    if seg_neighbors:
        raw.append({"neighbors": seg_neighbors})

    return raw, all_neighbors


async def retrieve_by_vector(
    qdrant: QdrantClient,
    collection: str,
    query_vector: list[float],
    k: int = 11,
    media: str | None = None,
    exclude_strain: str | None = None,
    vector_name: str | None = None,
) -> tuple[list[dict[str, Any]], list[NeighborResult]]:
    """Query Qdrant with a raw vector, return raw results and all neighbors."""
    from ..config import get_qdrant_settings
    from ..qdrant.operations import query_points_by_image

    settings = get_qdrant_settings()
    filter_spec = FilterSpec()
    if media is not None:
        filter_spec.media = media
    if exclude_strain is not None:
        filter_spec.exclude_strain = exclude_strain

    result = query_points_by_image(
        qdrant,
        query_vector,
        feature_type=vector_name or settings.default_vector_name,
        k=k,
        filter_spec=filter_spec,
        collection_name=collection,
    )

    strain_map: dict[str, str] = {}
    all_neighbors: list[NeighborResult] = []
    raw: list[dict[str, Any]] = []

    seg_neighbors: list[dict[str, Any]] = []
    for neighbor in result.neighbors:
        strain_map[neighbor.strain or ""] = (
            neighbor.specy or neighbor.strain or "unknown"
        )
        raw_entry = _neighbor_to_raw(neighbor, strain_map)
        seg_neighbors.append(raw_entry)
        all_neighbors.append(neighbor)

    if seg_neighbors:
        raw.append({"neighbors": seg_neighbors})

    return raw, all_neighbors


def run_aggregation(
    raw_results: list[dict[str, Any]],
    strain_map: dict[str, str],
    k: int,
    strategy: str = "freq_strength",
) -> Any:
    """Run aggregation with specified strategy. Returns AggregationResult."""
    return aggregate_predictions(
        raw_results,
        strain_to_specy=strain_map,
        k=k,
        strategy=strategy,
    )


RESEARCH_DEFAULTS = {
    "extractor": "EfficientNetB1_finetuned",
    "media_strategy": "same_media",
    "aggregation": "freq_strength",
    "k": 11,
    "collection": "myco_fungi_features_full_finetuned",
}
