import pytest
from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(name="user_headers")
def fixture_user_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="owner_headers")
def fixture_owner_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_training_status(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/training/status", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_list_jobs_requires_owner(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/training/jobs", headers=user_headers)
    assert resp.status_code == 403

    resp = client.get("/api/v1/training/jobs", headers=owner_headers)
    assert resp.status_code == 200


def test_trigger_training(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/training/trigger",
        json={"reason": "New data available"},
        headers=owner_headers,
    )
    assert resp.status_code == 202
    assert resp.json()["status"] == "processing"


def test_cancel_training(client: TestClient, owner_headers: dict[str, str]) -> None:
    trigger = client.post("/api/v1/training/trigger", json={}, headers=owner_headers)
    job_id = trigger.json()["id"]
    resp = client.post(f"/api/v1/training/jobs/{job_id}/cancel", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


def test_deploy_model(client: TestClient, owner_headers: dict[str, str]) -> None:
    trigger = client.post("/api/v1/training/trigger", json={}, headers=owner_headers)
    job_id = trigger.json()["id"]
    resp = client.post(
        f"/api/v1/training/jobs/{job_id}/deploy",
        json={"force": False},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id


def test_rollback(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post("/api/v1/training/rollback", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rollback_complete"
