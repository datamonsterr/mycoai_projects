import uuid

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


def test_start_query_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    """New DB-based retrieval returns 404 when image not found."""
    resp = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": _VALID_UUID,
            "k": 5,
            "aggregation": "weighted",
            "environment_strategy": "E1",
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


def test_query_sync_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/retrieval/query-sync",
        json={
            "image_id": _VALID_UUID,
            "k": 3,
            "aggregation": "avg",
            "environment_strategy": "E2",
        },
        headers=headers,
    )
    assert resp.status_code == 404
