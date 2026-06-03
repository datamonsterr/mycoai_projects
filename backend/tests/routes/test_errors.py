import pytest
from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(app)


def test_404_returns_problem_details(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/species/nonexistent-123", headers=headers)
    assert r.status_code == 404
    data = r.json()
    assert data["type"] == "https://api.mycoai.dev/errors/not-found"
    assert data["title"] == "Resource Not Found"
    assert data["status"] == 404
    assert "detail" in data
    assert "instance" in data


def test_401_returns_problem_details(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authentication"
    assert data["title"] == "Authentication Failed"


def test_403_returns_problem_details(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/api/v1/species",
        json={"name": "Should Fail"},
        headers=headers,
    )
    assert r.status_code == 403
    data = r.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authorization"


def test_paginated_response_format(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/v1/species?offset=0&limit=50", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert "total" in data
    assert "offset" in data
    assert data["offset"] == 0
    assert "limit" in data
    assert data["limit"] == 50


def test_healthcheck_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_root_exposes_key_endpoints(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "MycoAI Retrieval Backend"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"
