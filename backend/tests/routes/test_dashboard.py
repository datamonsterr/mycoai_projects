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


def test_dashboard_stats(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/stats", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_species" in data
    assert "total_strains" in data
    assert "total_images" in data


def test_chart_species(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/charts/species-distribution", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_chart_media(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/charts/media-distribution", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_chart_timeline(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/charts/timeline", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_qdrant_status(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/qdrant-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "points_count" in data


def test_chart_strain(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/charts/strain-distribution", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_chart_media_distribution(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/dashboard/charts/media-distribution", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
