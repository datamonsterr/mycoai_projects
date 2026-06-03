from __future__ import annotations

import threading
from functools import lru_cache

from qdrant_client import QdrantClient

from ..config import QdrantSettings, get_qdrant_settings

_client: QdrantClient | None = None
_lock = threading.Lock()


def init_qdrant_client(
    settings: QdrantSettings | None = None,
) -> QdrantClient:
    global _client
    if settings is None:
        settings = get_qdrant_settings()
    with _lock:
        if settings.url:
            _client = QdrantClient(
                url=settings.url,
                api_key=settings.api_key,
                prefer_grpc=settings.prefer_grpc,
                timeout=settings.timeout_seconds,
            )
        else:
            _client = QdrantClient(
                host=settings.host,
                port=settings.port,
                grpc_port=settings.grpc_port,
                prefer_grpc=settings.prefer_grpc,
                timeout=settings.timeout_seconds,
            )
    return _client


def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        return init_qdrant_client()
    return _client


@lru_cache(maxsize=1)
def get_collection_name() -> str:
    return get_qdrant_settings().collection_name
