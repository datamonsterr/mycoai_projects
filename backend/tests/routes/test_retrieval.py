import uuid
from pathlib import Path
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


def test_build_strain_map_prefers_canonical_csv(tmp_path: Path) -> None:
    import asyncio

    csv_path = tmp_path / "Dataset" / "strain_to_specy.csv"
    csv_path.parent.mkdir(parents=True)
    csv_path.write_text("Strain,Species\nDTO 162-C6,Penicillium freii\n")
    db = SimpleNamespace(execute=AsyncMock())

    with patch("backend.api.retrieval.Path.cwd", return_value=tmp_path):
        from backend.api.retrieval import _build_strain_map

        strain_map = asyncio.run(_build_strain_map(db))

    assert strain_map == {"DTO 162-C6": "Penicillium freii"}
    db.execute.assert_not_called()


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
        qdrant_point_id=uuid.uuid4(),
        is_archived=False,
        segment_index=0,
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
    saved_neighbor = created_results[0].neighbors[0]
    assert saved_neighbor.neighbor_image_id == "neighbor-image-1"
    _, kwargs = patched_query.call_args
    assert kwargs["filter_spec"].media == "CYA"
    assert kwargs["filter_spec"].exclude_strain == "DTO 148-F1"


def test_get_job_results_uses_retrieval_evidence_fallback_for_segment_path() -> None:
    import asyncio

    job_id = uuid.uuid4()
    result_id = uuid.uuid4()
    job = SimpleNamespace(
        id=job_id,
        status="completed",
        config={"threshold": None, "queried_images": []},
    )
    result = SimpleNamespace(
        id=result_id,
        rank=1,
        species_name="Penicillium chrysogenum",
        score=0.91,
        strain_name="DTO 148-F1",
    )
    neighbor = SimpleNamespace(
        neighbor_strain="DTO 148-F2",
        neighbor_species="Penicillium chrysogenum",
        similarity=0.88,
        media="CYA",
        neighbor_image_id=None,
        segment_path="Dataset/prepared/DTO_148_F2/segment_2.jpg",
    )

    class FakeExecuteResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    db = SimpleNamespace(
        scalar=AsyncMock(return_value=job),
        execute=AsyncMock(
            side_effect=[
                FakeExecuteResult([result]),
                FakeExecuteResult([neighbor]),
            ]
        ),
    )
    user = SimpleNamespace(id=uuid.uuid4())

    from backend.api.retrieval import get_job_results

    response = asyncio.run(get_job_results(str(job_id), user, db))

    assert response["rankings"][0]["neighbors"][0]["image_thumbnail_url"].startswith(
        "/api/v1/retrieval/"
    )


def test_get_retrieval_evidence_rejects_path_traversal(client: TestClient) -> None:
    response = client.get(
        "/api/v1/retrieval/evidence",
        params={"segment_path": "../../etc/passwd"},
    )

    assert response.status_code == 404


def test_start_query_stores_neighbor_fallback_for_segment_path() -> None:
    import asyncio

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
                image_id=None,
                score=0.91,
                strain="DTO 148-F2",
                media="CYA",
                specy="Penicillium chrysogenum",
                segment_index=2,
                extractor="EfficientNetB1_finetuned",
                segment_path="Dataset/prepared/DTO_148_F2/segment_2.jpg",
            )
        ],
        total=1,
    )
    image = SimpleNamespace(
        id=uuid.UUID(_VALID_UUID),
        media=SimpleNamespace(name="CYA"),
        strain=SimpleNamespace(name="DTO 148-F1"),
        segments=[
            SimpleNamespace(
                qdrant_point_id=uuid.uuid4(), is_archived=False, segment_index=0
            )
        ],
    )

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

    created_jobs: list[object] = []

    def fake_add(obj, *_args, **_kwargs):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if obj.__class__.__name__ == "RetrievalJob":
            created_jobs.append(obj)

    db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                FakeExecuteResult([image]),
                FakeExecuteResult(scalar_value="Penicillium chrysogenum"),
            ]
        ),
        add=fake_add,
        flush=AsyncMock(),
        commit=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid.uuid4())

    aggregation_result = SimpleNamespace(
        ranking=[SimpleNamespace(species="Penicillium chrysogenum", score=0.91)]
    )

    with (
        patch("backend.api.retrieval.query_points_by_id", return_value=query_result),
        patch(
            "backend.api.retrieval.aggregate_predictions",
            return_value=aggregation_result,
        ),
        patch(
            "backend.api.retrieval._build_strain_map",
            new=AsyncMock(return_value={"DTO 148-F2": "Penicillium chrysogenum"}),
        ),
        patch(
            "backend.api.retrieval.get_qdrant_client",
            return_value=object(),
        ),
        patch(
            "backend.api.retrieval.get_collection_name",
            return_value="segments",
        ),
        patch(
            "backend.api.retrieval._query_by_crop_image",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "backend.api.retrieval._resolve_species_sync",
            return_value="Penicillium chrysogenum",
        ),
        patch(
            "backend.api.retrieval._resolve_species_fast",
            return_value="Penicillium chrysogenum",
        ),
    ):
        from backend.api.retrieval import start_query

        asyncio.run(start_query(payload, user, db))

    assert created_jobs
    stored_neighbor = created_jobs[0].config["queried_images"][0]["neighbors"][0]
    assert stored_neighbor["image_thumbnail_url"].startswith("/api/v1/retrieval/")


def test_batch_results_use_batch_strain_label() -> None:
    import asyncio

    payload = SimpleNamespace(
        image_id=_VALID_UUID,
        image_ids=[_VALID_UUID, str(uuid.uuid4())],
        k=3,
        aggregation="freq_strength",
        media_strategy="same_media",
    )
    from backend.qdrant.models import NeighborResult, QueryResult

    image_a = SimpleNamespace(
        id=uuid.UUID(_VALID_UUID),
        media=SimpleNamespace(name="CYA"),
        strain=SimpleNamespace(name="DTO 148-F1"),
        segments=[
            SimpleNamespace(
                qdrant_point_id=uuid.uuid4(),
                is_archived=False,
                segment_index=0,
            )
        ],
    )
    image_b = SimpleNamespace(
        id=uuid.UUID(payload.image_ids[1]),
        media=SimpleNamespace(name="CYA"),
        strain=SimpleNamespace(name="DTO 148-F2"),
        segments=[
            SimpleNamespace(
                qdrant_point_id=uuid.uuid4(),
                is_archived=False,
                segment_index=0,
            )
        ],
    )

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
                FakeExecuteResult([image_a, image_b]),
            ]
        ),
        add=fake_add,
        flush=AsyncMock(),
        commit=AsyncMock(),
    )
    user = SimpleNamespace(id=uuid.uuid4())
    aggregation_result = SimpleNamespace(
        ranking=[SimpleNamespace(species="Penicillium chrysogenum", score=0.91)]
    )

    with (
        patch(
            "backend.api.retrieval.query_points_by_id",
            return_value=QueryResult(
                neighbors=[
                    NeighborResult(
                        image_id="neighbor-image-1",
                        score=0.91,
                        strain="DTO 148-F9",
                        media="CYA",
                        specy="Penicillium chrysogenum",
                        extractor="EfficientNetB1_finetuned",
                    )
                ],
                total=1,
            ),
        ),
        patch(
            "backend.api.retrieval.aggregate_predictions",
            return_value=aggregation_result,
        ),
        patch(
            "backend.api.retrieval._build_strain_map",
            new=AsyncMock(return_value={}),
        ),
        patch("backend.api.retrieval.get_qdrant_client", return_value=object()),
        patch("backend.api.retrieval.get_collection_name", return_value="segments"),
        patch(
            "backend.api.retrieval._query_by_crop_image",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "backend.api.retrieval._resolve_species_sync",
            return_value="Penicillium chrysogenum",
        ),
        patch(
            "backend.api.retrieval._resolve_species_fast",
            return_value="Penicillium chrysogenum",
        ),
        patch(
            "backend.api.retrieval.is_known_confidence",
            return_value={
                "formula": "gnorm_0_2",
                "confidence": 0.0,
                "threshold": 0.12,
                "is_known": True,
            },
        ),
    ):
        from backend.api.retrieval import start_query

        asyncio.run(start_query(payload, user, db))

    assert created_results
    assert created_results[0].strain_name == "batch"
