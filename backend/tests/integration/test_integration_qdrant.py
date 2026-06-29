from __future__ import annotations

import uuid

import pytest
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.config import get_qdrant_settings

pytestmark = [pytest.mark.integration, pytest.mark.integration_qdrant]

TEST_COLLECTION = "test_integration_points"


def _collection_name() -> str:
    return get_qdrant_settings().collection_name


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_qdrant_connection_health(qdrant_client) -> None:
    cols = qdrant_client.get_collections()
    assert cols is not None


@pytest.mark.asyncio
async def test_qdrant_collection_exists(qdrant_client) -> None:
    collection = _collection_name()
    cols = qdrant_client.get_collections()
    names = [c.name for c in cols.collections]
    if collection not in names:
        pytest.skip(f"Collection '{collection}' not found")
    assert collection in names


@pytest.mark.asyncio
async def test_qdrant_get_collection_info(qdrant_client) -> None:
    collection = _collection_name()
    cols = qdrant_client.get_collections()
    names = [c.name for c in cols.collections]
    if collection not in names:
        pytest.skip(f"Collection '{collection}' not found")

    info = qdrant_client.get_collection(collection_name=collection)
    assert info is not None
    vectors = info.config.params.vectors
    if isinstance(vectors, dict):
        first_vector = next(iter(vectors.values()))
        vector_size = first_vector.size
    else:
        vector_size = vectors.size
    assert isinstance(vector_size, int)
    assert vector_size > 0


@pytest.mark.asyncio
async def test_qdrant_upsert_and_search(qdrant_client) -> None:
    try:
        qdrant_client.create_collection(
            collection_name=TEST_COLLECTION,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
    except Exception:
        pass

    point_id = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    point = PointStruct(
        id=point_id,
        vector=[0.1, 0.2, 0.3, 0.4],
        payload={"species": "Test Species", "strain": "TS-001", "media": "MEA"},
    )
    qdrant_client.upsert(collection_name=TEST_COLLECTION, points=[point])

    result = qdrant_client.query_points(
        collection_name=TEST_COLLECTION,
        query=[0.1, 0.2, 0.3, 0.4],
        limit=3,
        with_payload=True,
    )
    points = result.points
    assert len(points) >= 1
    found = [p for p in points if p.id == point_id]
    assert len(found) == 1
    assert found[0].payload["species"] == "Test Species"

    qdrant_client.delete(
        collection_name=TEST_COLLECTION,
        points_selector=[point_id],
    )
    qdrant_client.delete_collection(collection_name=TEST_COLLECTION)


@pytest.mark.asyncio
async def test_qdrant_filtered_search(qdrant_client) -> None:
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    try:
        qdrant_client.create_collection(
            collection_name=TEST_COLLECTION,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
    except Exception:
        pass

    id_a = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    id_b = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
    qdrant_client.upsert(
        collection_name=TEST_COLLECTION,
        points=[
            PointStruct(
                id=id_a,
                vector=[1.0, 0.0, 0.0, 0.0],
                payload={"media": "MEA", "strain": "A"},
            ),
            PointStruct(
                id=id_b,
                vector=[0.0, 1.0, 0.0, 0.0],
                payload={"media": "PDA", "strain": "B"},
            ),
        ],
    )

    result = qdrant_client.query_points(
        collection_name=TEST_COLLECTION,
        query=[1.0, 0.0, 0.0, 0.0],
        query_filter=Filter(
            must=[FieldCondition(key="media", match=MatchValue(value="MEA"))]
        ),
        limit=3,
        with_payload=True,
    )
    points = result.points
    assert len(points) >= 1
    for p in points:
        assert p.payload.get("media") == "MEA"

    qdrant_client.delete(collection_name=TEST_COLLECTION, points_selector=[id_a, id_b])
    qdrant_client.delete_collection(collection_name=TEST_COLLECTION)


@pytest.mark.asyncio
async def test_qdrant_batch_upsert(qdrant_client) -> None:
    try:
        qdrant_client.create_collection(
            collection_name=TEST_COLLECTION,
            vectors_config=VectorParams(size=4, distance=Distance.COSINE),
        )
    except Exception:
        pass

    ids = []
    batch = []
    for i in range(5):
        pid = uuid.uuid4().int & 0x7FFFFFFFFFFFFFFF
        ids.append(pid)
        batch.append(
            PointStruct(
                id=pid,
                vector=[float(i), float(i + 1), float(i + 2), float(i + 3)],
                payload={"batch_idx": i},
            )
        )
    qdrant_client.upsert(collection_name=TEST_COLLECTION, points=batch)

    info = qdrant_client.get_collection(collection_name=TEST_COLLECTION)
    assert info.points_count >= 5

    qdrant_client.delete(collection_name=TEST_COLLECTION, points_selector=ids)
    qdrant_client.delete_collection(collection_name=TEST_COLLECTION)
