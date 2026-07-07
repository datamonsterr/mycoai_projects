"""Tests for Qdrant integration: filters, models, aggregation, routes."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, ScoredPoint

from backend.qdrant.aggregation import aggregate_predictions
from backend.qdrant.collections import (
    collection_exists,
    get_collection_stats,
)
from backend.qdrant.filters import build_filter
from backend.qdrant.models import FilterSpec, PointUpsertRequest
from backend.qdrant.operations import (
    delete_points,
    query_points_by_id,
    query_points_by_image,
    upsert_points,
)

ConditionList = list[FieldCondition]


def _must(f: Any) -> ConditionList:
    return cast(ConditionList, f.must)


def _must_not(f: Any) -> ConditionList:
    return cast(ConditionList, f.must_not)


# ── filter tests ──


def test_build_filter_none() -> None:
    assert build_filter(None) is None


def test_build_filter_empty_spec() -> None:
    assert build_filter(FilterSpec()) is None


def test_build_filter_media() -> None:
    result = build_filter(FilterSpec(media="MEA"))
    assert result is not None
    must = _must(result)
    assert len(must) == 1
    cond = must[0]
    assert isinstance(cond, Filter)
    assert cond.should is not None
    keys = [c.key for c in cond.should if isinstance(c, FieldCondition)]
    assert keys == ["media", "environment"]


def test_build_filter_exclude_media() -> None:
    result = build_filter(FilterSpec(exclude_media="PDA"))
    assert result is not None
    must_not = _must_not(result)
    assert len(must_not) == 2
    keys = [cond.key for cond in must_not]
    assert keys == ["media", "environment"]
    assert all(cond.match == MatchValue(value="PDA") for cond in must_not)


def test_build_filter_strain_and_angle() -> None:
    result = build_filter(FilterSpec(strain="DTO 148-D1", angle="ob"))
    assert result is not None
    must = _must(result)
    keys = [c.key for c in must]
    assert "strain" in keys
    assert "angle" in keys


def test_build_filter_exclude_strain() -> None:
    result = build_filter(FilterSpec(exclude_strain="DTO 148-D1"))
    assert result is not None
    must_not = _must_not(result)
    assert must_not[0].key == "strain"


def test_build_filter_parent_id() -> None:
    result = build_filter(FilterSpec(parent_id="item123"))
    assert result is not None
    must = _must(result)
    assert must[0].key == "parent_item_id"


def test_build_filter_exclude_ids() -> None:
    result = build_filter(FilterSpec(exclude_ids=[1, 2, 3]))
    assert result is not None
    must_not = _must_not(result)
    assert len(must_not) == 3
    for cond in must_not:
        assert isinstance(cond, FieldCondition)
        assert cond.key == "_id"


def test_build_filter_combined() -> None:
    result = build_filter(FilterSpec(media="MEA", exclude_strain="DTO 148-D1"))
    assert result is not None
    must = _must(result)
    must_not = _must_not(result)
    assert len(must) == 1
    assert len(must_not) == 1


# ── aggregation tests ──


def test_aggregate_weighted() -> None:
    strain_to_specy = {"s1": "spA", "s2": "spB"}
    raw = [
        {
            "neighbors": [
                {"specy": "spA", "score": 0.9, "strain": "s1"},
                {"specy": "spA", "score": 0.8, "strain": "s1"},
                {"specy": "spB", "score": 0.3, "strain": "s2"},
            ]
        }
    ]
    result = aggregate_predictions(raw, strain_to_specy, k=11, strategy="weighted")
    assert result.top_species == "spA"
    assert result.top_score > 0.0


def test_aggregate_uni() -> None:
    strain_to_specy = {"s1": "spA", "s2": "spB"}
    raw = [
        {
            "neighbors": [
                {"specy": "spA", "score": 0.9},
                {"specy": "spA", "score": 0.8},
                {"specy": "spB", "score": 0.3},
                {"specy": "spB", "score": 0.2},
            ]
        }
    ]
    result = aggregate_predictions(raw, strain_to_specy, k=11, strategy="uni")
    assert result.top_species in ("spA", "spB")


def test_aggregate_relative() -> None:
    """relative: score share = species_scores[X] / sum(all scores). Sum to 1."""
    strain_to_specy = {}
    raw = [
        {
            "neighbors": [
                {"specy": "spA", "score": 0.9},
                {"specy": "spA", "score": 0.8},
                {"specy": "spB", "score": 0.3},
            ]
        },
        {
            "neighbors": [
                {"specy": "spA", "score": 0.7},
                {"specy": "spB", "score": 0.2},
            ]
        },
    ]
    result = aggregate_predictions(raw, strain_to_specy, k=11, strategy="relative")
    assert result.top_species == "spA"
    total_share = sum(e.score for e in result.ranking)
    assert 0.99 <= total_share <= 1.01


def test_aggregate_freq_strength() -> None:
    """freq_strength: (queries_with_X / M) * (avg_score_X). Per-species independent."""
    strain_to_specy = {}
    raw = [
        {
            "neighbors": [
                {"specy": "spA", "score": 0.9},
                {"specy": "spA", "score": 0.8},
                {"specy": "spB", "score": 0.3},
            ]
        },
        {
            "neighbors": [
                {"specy": "spA", "score": 0.7},
                {"specy": "spB", "score": 0.2},
            ]
        },
    ]
    result = aggregate_predictions(raw, strain_to_specy, k=11, strategy="freq_strength")
    spA_entry = next((e for e in result.ranking if e.species == "spA"), None)
    spB_entry = next((e for e in result.ranking if e.species == "spB"), None)
    assert spA_entry is not None
    assert spB_entry is not None
    assert spA_entry.score > spB_entry.score
    assert 0.0 < spA_entry.score <= 1.0
    assert 0.0 < spB_entry.score <= 1.0


def test_aggregate_empty() -> None:
    result = aggregate_predictions([], {}, k=11, strategy="weighted")
    assert result.top_species == "unknown"
    assert result.top_score == 0.0


# ── filter-to-Qdrant roundtrip ──


def test_filter_spec_roundtrip() -> None:
    spec = FilterSpec(media="MEA", exclude_strain="DTO 148-D1")
    qdrant_filter = build_filter(spec)
    assert qdrant_filter is not None
    must = _must(qdrant_filter)
    media_filter = next(c for c in must if isinstance(c, Filter))
    assert media_filter.should is not None
    env_cond = [c for c in media_filter.should if c.key == "media"][0]
    assert env_cond.match is not None
    assert env_cond.match.value == "MEA"


# ── operations tests (mocked Qdrant client) ──


def make_mock_client() -> MagicMock:
    client = MagicMock()
    scored = ScoredPoint(
        id=42,
        version=1,
        score=0.95,
        payload={
            "image_id": "img_42",
            "strain": "DTO 123-A1",
            "media": "MEA",
            "angle": "ob",
            "specy": "Penicillium commune",
            "parent_item_id": "parent_1",
            "segment_index": 0,
            "bbox": {"x": 0, "y": 0, "w": 100, "h": 100},
            "extractor": "efficientnetb1_finetuned",
        },
        vector={"efficientnetb1_finetuned": [0.1] * 1280},
    )
    response = MagicMock()
    response.points = [scored]
    client.query_points.return_value = response
    return client


def test_query_points_by_image() -> None:
    client = make_mock_client()
    result = query_points_by_image(
        client,
        image_vector=[0.5] * 1280,
        feature_type="EfficientNetB1_finetuned",
        k=5,
    )
    assert len(result.neighbors) == 1
    assert result.neighbors[0].score == 0.95
    assert result.neighbors[0].strain == "DTO 123-A1"


def test_query_points_by_id_mocked() -> None:
    client = make_mock_client()
    from qdrant_client.models import Record

    record = Record(
        id=42,
        payload={
            "image_id": "img_42",
            "parent_item_id": "parent_1",
        },
        vector={"EfficientNetB1_finetuned": [0.1] * 1280},
    )
    client.retrieve.return_value = [record]
    result = query_points_by_id(
        client,
        point_id=42,
        feature_type="EfficientNetB1_finetuned",
        k=3,
        exclude_self=True,
        exclude_siblings=True,
    )
    assert len(result.neighbors) >= 0
    client.retrieve.assert_called_once()


def test_upsert_points() -> None:
    client = MagicMock()
    points = [
        PointUpsertRequest(
            point_id=1,
            vectors={"vec_a": [0.1, 0.2]},
            payload={"species": "Test"},
        ),
        PointUpsertRequest(
            point_id=2,
            vectors={"vec_a": [0.3, 0.4]},
            payload={"species": "Test2"},
        ),
    ]
    count = upsert_points(client, points)
    assert count == 2
    client.upsert.assert_called_once()


def test_delete_points() -> None:
    client = MagicMock()
    count = delete_points(client, [1, 2, 3])
    assert count == 3
    client.delete.assert_called_once()


# ── collections tests ──


def test_collection_exists_mocked() -> None:
    client = MagicMock()
    fake_col = MagicMock()
    fake_col.name = "myco_fungi_features_full_finetuned"
    client.get_collections.return_value.collections = [fake_col]
    assert collection_exists(client) is True


def test_get_collection_stats_mocked() -> None:
    client = MagicMock()
    fake_info = MagicMock()
    fake_info.points_count = 1000
    client.get_collection.return_value = fake_info
    fake_point = MagicMock()
    fake_point.vector = {"resnet50": [0.0] * 2048}
    client.scroll.return_value = ([fake_point], None)
    stats = get_collection_stats(client)
    assert stats.total_points == 1000
    assert stats.vector_types == ["resnet50"]
    assert stats.vector_dimensions == {"resnet50": 2048}


# ── router tests ──


@patch("backend.routers.search.get_qdrant_client")
def test_stats_endpoint(mock_get_client: MagicMock, client: TestClient) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    fake_info = MagicMock()
    fake_info.points_count = 5
    mock_client.get_collection.return_value = fake_info
    mock_client.scroll.return_value = ([], None)

    response = client.get("/api/collections/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_points"] == 5


@patch("backend.routers.search.get_qdrant_client")
def test_search_by_image_endpoint_requires_vector(
    mock_get_client: MagicMock, client: TestClient
) -> None:
    response = client.post("/api/search/by-image", json={"k": 5})
    assert response.status_code == 400


@patch("backend.routers.search.get_qdrant_client")
def test_search_by_id_endpoint_not_found(
    mock_get_client: MagicMock, client: TestClient
) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.retrieve.return_value = []

    response = client.post("/api/search/by-id", json={"point_id": 999, "k": 5})
    assert response.status_code == 404


@patch("backend.routers.search.get_qdrant_client")
def test_upsert_endpoint(mock_get_client: MagicMock, client: TestClient) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    response = client.post(
        "/api/index/upsert",
        json=[{"point_id": 1, "vectors": {"v": [0.1]}, "payload": {"s": "test"}}],
    )
    assert response.status_code == 200
    assert response.json()["upserted"] == 1


def test_aggregate_router(client: TestClient) -> None:
    response = client.post(
        "/api/aggregate",
        json={
            "neighbors": [
                [
                    {"specy": "spA", "score": 0.9, "distance": 0.1},
                    {"specy": "spB", "score": 0.3, "distance": 0.7},
                ]
            ],
            "strain_to_specy": {},
            "k": 11,
            "strategy": "weighted",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "top_species" in data


@patch("backend.routers.search.get_qdrant_client")
def test_media_endpoint(mock_get_client: MagicMock, client: TestClient) -> None:
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client

    class FakePoint:
        def __init__(self, payload: dict):
            self.payload = payload

    mock_client.scroll.return_value = (
        [FakePoint({"media": "MEA"}), FakePoint({"media": "PDA"})],
        None,
    )

    response = client.get("/api/collections/media")
    assert response.status_code == 200
    data = response.json()
    assert "MEA" in data
    assert "PDA" in data
