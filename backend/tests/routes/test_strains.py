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


@pytest.fixture(name="species_id")
def fixture_species_id(client: TestClient, owner_headers: dict[str, str]) -> str:
    resp = client.post(
        "/api/v1/species",
        json={"name": "Test Species for Strains"},
        headers=owner_headers,
    )
    # 201 if created, 409 if already exists
    if resp.status_code == 409:
        # Get existing
        list_resp = client.get("/api/v1/species", headers=owner_headers)
        for s in list_resp.json()["items"]:
            if s["name"] == "Test Species for Strains":
                return s["id"]
    return resp.json()["id"]


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
    client: TestClient,
    user_headers: dict[str, str],
    owner_headers: dict[str, str],
    species_id: str,
) -> None:
    payload = {"name": "New Strain", "species_id": species_id}
    resp = client.post("/api/v1/strains", json=payload, headers=user_headers)
    assert resp.status_code == 403

    resp = client.post("/api/v1/strains", json=payload, headers=owner_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "New Strain"


def test_get_strain_not_found(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/strains/00000000-0000-0000-0000-000000000000",
        headers=user_headers,
    )
    assert resp.status_code == 404


def test_delete_strain(
    client: TestClient,
    owner_headers: dict[str, str],
    species_id: str,
) -> None:
    create = client.post(
        "/api/v1/strains",
        json={"name": "Deletable Strain", "species_id": species_id},
        headers=owner_headers,
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/v1/strains/{sid}", headers=owner_headers)
    assert resp.status_code == 204


def test_strain_restore_and_clean(
    client: TestClient,
    owner_headers: dict[str, str],
    species_id: str,
) -> None:
    create = client.post(
        "/api/v1/strains",
        json={"name": "Trash Strain", "species_id": species_id, "source": "test"},
        headers=owner_headers,
    )
    strain_id = create.json()["id"]

    archive = client.delete(f"/api/v1/strains/{strain_id}", headers=owner_headers)
    assert archive.status_code == 204

    archived_list = client.get(
        "/api/v1/strains?is_archived=true",
        headers=owner_headers,
    )
    assert archived_list.status_code == 200
    assert any(item["id"] == strain_id for item in archived_list.json()["items"])

    restore = client.post(f"/api/v1/strains/{strain_id}/restore", headers=owner_headers)
    assert restore.status_code == 200
    assert restore.json()["is_archived"] is False

    client.delete(f"/api/v1/strains/{strain_id}", headers=owner_headers)
    clean = client.delete(f"/api/v1/strains/{strain_id}/clean", headers=owner_headers)
    assert clean.status_code == 204

    missing = client.get(f"/api/v1/strains/{strain_id}", headers=owner_headers)
    assert missing.status_code == 404
