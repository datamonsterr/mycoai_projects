from __future__ import annotations

from qdrant_client import QdrantClient

from ..config import get_qdrant_settings
from .models import CollectionStats


def collection_exists(client: QdrantClient, collection_name: str | None = None) -> bool:
    collection = collection_name or get_qdrant_settings().collection_name
    return any(col.name == collection for col in client.get_collections().collections)


def get_collection_stats(
    client: QdrantClient,
    collection_name: str | None = None,
) -> CollectionStats:
    collection = collection_name or get_qdrant_settings().collection_name
    info = client.get_collection(collection_name=collection)
    sample_points, _ = client.scroll(
        collection_name=collection,
        limit=1,
        with_vectors=True,
        with_payload=True,
    )
    vector_types: list[str] = []
    vector_dimensions: dict[str, int] = {}
    if sample_points:
        point = sample_points[0]
        vectors = getattr(point, "vector", {})
        if isinstance(vectors, dict):
            vector_types = list(vectors.keys())
            for name, vector in vectors.items():
                if isinstance(vector, list):
                    vector_dimensions[name] = len(vector)
    return CollectionStats(
        total_points=getattr(info, "points_count", None),
        vector_types=vector_types,
        vector_dimensions=vector_dimensions,
        collection_name=collection,
    )


def list_environments(
    client: QdrantClient, collection_name: str | None = None
) -> list[str]:
    collection = collection_name or get_qdrant_settings().collection_name
    environments: set[str] = set()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=True,
        )
        for point in points:
            payload = dict(point.payload or {})
            environment = payload.get("environment", "unknown")
            if environment and environment != "unknown":
                environments.add(str(environment))
        if offset is None:
            break
    return sorted(environments)
