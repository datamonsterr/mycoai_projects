import pytest
from fastapi.testclient import TestClient


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


def test_list_strains(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/strains", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_list_strains_filtered(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/strains?search=DTO&offset=0&limit=10", headers=user_headers
    )
    assert resp.status_code == 200


def test_create_strain_requires_owner(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    payload = {"name": "New Strain", "species_id": "fake-species-id"}
    resp = client.post("/api/v1/strains", json=payload, headers=user_headers)
    assert resp.status_code == 403

    resp = client.post("/api/v1/strains", json=payload, headers=owner_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Strain"


def test_get_strain_not_found(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/strains/nonexistent", headers=user_headers)
    assert resp.status_code == 404


def test_delete_strain(client: TestClient, owner_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/strains",
        json={"name": "Deletable Strain", "species_id": "fake-species-id"},
        headers=owner_headers,
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/v1/strains/{sid}", headers=owner_headers)
    assert resp.status_code == 204
