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


def test_list_species(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/species", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


def test_create_species_requires_owner(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/species",
        json={"name": "New Species", "description": "test"},
        headers=user_headers,
    )
    assert resp.status_code == 403

    resp = client.post(
        "/api/v1/species",
        json={"name": "New Species", "description": "test"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Species"


def test_get_species_not_found(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/species/00000000-0000-0000-0000-000000000000", headers=user_headers
    )
    assert resp.status_code == 404


def test_update_species(client: TestClient, owner_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/species",
        json={"name": "Updatable"},
        headers=owner_headers,
    )
    sid = create.json()["id"]
    resp = client.patch(
        f"/api/v1/species/{sid}",
        json={"name": "Updated Name"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Name"


def test_delete_species(client: TestClient, owner_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/species",
        json={"name": "Deletable"},
        headers=owner_headers,
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/v1/species/{sid}", headers=owner_headers)
    assert resp.status_code == 204
