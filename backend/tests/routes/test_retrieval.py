import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(name="headers")
def fixture_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


_VALID_UUID = str(uuid.uuid4())


def test_start_query_image_not_found(
    client: TestClient, headers: dict[str, str]
) -> None:
    """New DB-based retrieval returns 404 when image not found."""
    resp = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": _VALID_UUID,
            "k": 5,
            "aggregation": "freq_strength",
            "media_strategy": "same_media",
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_get_job_status_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get(f"/api/v1/retrieval/jobs/{_VALID_UUID}", headers=headers)
    assert resp.status_code == 404


def test_get_job_results_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get(f"/api/v1/retrieval/jobs/{_VALID_UUID}/results", headers=headers)
    assert resp.status_code == 404


def test_query_sync_image_not_found(
    client: TestClient, headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/retrieval/query-sync",
        json={
            "image_id": _VALID_UUID,
            "k": 3,
            "aggregation": "freq_strength",
            "media_strategy": "same_media",
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_query_sync_uses_same_media_filter_and_neighbor_source_url(
    client: TestClient,
    headers: dict[str, str],
) -> None:
    del client, headers
    payload = SimpleNamespace(
        image_id=_VALID_UUID,
        k=3,
        aggregation="freq_strength",
        media_strategy="same_media",
    )
    from backend.qdrant.models import NeighborResult, QueryResult

    query_result = QueryResult(
        neighbors=[
            NeighborResult(
                image_id="neighbor-image-1",
                score=0.91,
                strain="DTO 148-F1",
                media="CYA",
                specy="Penicillium chrysogenum",
                segment_index=2,
                extractor="EfficientNetB1_finetuned",
            )
        ],
        total=1,
    )

    image = SimpleNamespace(
        id=uuid.UUID(_VALID_UUID),
        media=SimpleNamespace(name="CYA"),
        strain=SimpleNamespace(name="DTO 148-F1"),
        segments=[],
    )
    segment = SimpleNamespace(
        qdrant_point_id=uuid.uuid4(), is_archived=False, segment_index=0
    )
    image.segments = [segment]

    class FakeExecuteResult:
        def __init__(self, rows=None, scalar_value=None):
            self._rows = rows or []
            self._scalar_value = scalar_value

        def scalars(self):
            return self

        def all(self):
            return self._rows

        def scalar_one_or_none(self):
            return self._scalar_value

    created_results: list[object] = []

    def fake_add(obj, *_args, **_kwargs):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if obj.__class__.__name__ == "RetrievalResult":
            created_results.append(obj)

    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                FakeExecuteResult([image]),
                FakeExecuteResult(scalar_value="Penicillium chrysogenum"),
                FakeExecuteResult([("DTO 148-F1", "Penicillium chrysogenum")]),
            ]
        ),
        add=fake_add,
        flush=AsyncMock(),
        commit=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid.uuid4())

    with patch(
        "backend.api.retrieval.query_points_by_id",
        return_value=query_result,
    ) as patched_query:
        import asyncio

        from backend.api.retrieval import start_query

        response = asyncio.run(start_query(payload, user, db))

    assert response["status"] == "completed"
    assert created_results
    saved_neighbor = next(
        neighbor for result in created_results for neighbor in result.neighbors
    )
    assert saved_neighbor.neighbor_image_id == "neighbor-image-1"
    _, kwargs = patched_query.call_args
    assert kwargs["filter_spec"].media == "CYA"
