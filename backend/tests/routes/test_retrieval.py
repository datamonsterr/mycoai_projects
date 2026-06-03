import pytest
from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(name="headers")
def fixture_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_start_query(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "fake-image-id",
            "k": 5,
            "aggregation": "weighted",
            "environment_strategy": "E1",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    assert data["estimated_seconds"] == 5


def test_get_job_status(client: TestClient, headers: dict[str, str]) -> None:
    start = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "fake-image-id",
            "k": 5,
            "aggregation": "weighted",
            "environment_strategy": "E1",
        },
        headers=headers,
    )
    job_id = start.json()["job_id"]
    resp = client.get(f"/api/v1/retrieval/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id


def test_get_job_status_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/retrieval/jobs/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_get_job_results(client: TestClient, headers: dict[str, str]) -> None:
    start = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "fake-image-id",
            "k": 5,
            "aggregation": "weighted",
            "environment_strategy": "E1",
        },
        headers=headers,
    )
    job_id = start.json()["job_id"]
    resp = client.get(f"/api/v1/retrieval/jobs/{job_id}/results", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert len(data["rankings"]) == 1
    assert data["rankings"][0]["species"] == "Penicillium commune"


def test_query_sync(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/retrieval/query-sync",
        json={
            "image_id": "fake-image-id",
            "k": 3,
            "aggregation": "avg",
            "environment_strategy": "E2",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"
