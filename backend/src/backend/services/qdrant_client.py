from __future__ import annotations

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from ..config import get_qdrant_settings


class QdrantClientService:
    def __init__(self, collection_name: str | None = None) -> None:
        settings = get_qdrant_settings()
        self._client = QdrantClient(
            host=settings.host,
            port=settings.port,
            grpc_port=settings.grpc_port,
            prefer_grpc=settings.prefer_grpc,
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )
        self._collection = collection_name or settings.collection_name

    async def upsert_point(
        self,
        point_id: int,
        vectors: dict[str, list[float]],
        payload: dict[str, Any],
    ) -> None:
        import asyncio

        await asyncio.to_thread(
            self._client.upsert,
            collection_name=self._collection,
            points=[
                PointStruct(
                    id=point_id,
                    vector={k: v for k, v in vectors.items()},
                    payload=payload,
                )
            ],
        )

    async def query(
        self,
        vector: list[float],
        limit: int = 10,
        vector_name: str | None = None,
    ) -> list[dict[str, Any]]:
        import asyncio

        settings = get_qdrant_settings()
        vname = vector_name or settings.default_vector_name
        result = await asyncio.to_thread(
            self._client.query_points,
            collection_name=self._collection,
            query=vector,
            using=vname,
            limit=limit,
            with_payload=True,
        )
        return [dict(p.payload or {}) for p in result.points]
