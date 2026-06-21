import pytest
from fastapi.testclient import TestClient

from backend.api.media import router as media_router
from backend.app import create_app
from backend.database import get_db


@pytest.fixture(name="client")
def fixture_client(test_session_factory):
    app = create_app()
    app.include_router(media_router, prefix="/api/v1/media")
    app.dependency_overrides[get_db] = test_session_factory
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


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


def test_list_media(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/media", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_list_media_with_filters(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/media?is_archived=true&offset=0&limit=10", headers=user_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


def test_create_media_as_owner(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/media",
        json={"name": "Sabouraud Dextrose Agar", "description": "For dermatophytes"},
        headers=owner_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Sabouraud Dextrose Agar"
    assert data["description"] == "For dermatophytes"
    assert data["is_archived"] is False
    assert "id" in data
    assert "created_at" in data


def test_create_media_missing_name(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/media",
        json={"description": "No name provided"},
        headers=owner_headers,
    )
    assert resp.status_code == 422


def test_create_media_forbidden_as_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/media",
        json={"name": "User Attempt"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_get_media_by_id(
    client: TestClient, owner_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    create = client.post(
        "/api/v1/media",
        json={"name": "Corn Meal Agar"},
        headers=owner_headers,
    )
    mid = create.json()["id"]
    resp = client.get(f"/api/v1/media/{mid}", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Corn Meal Agar"
    assert data["id"] == mid


def test_get_media_not_found(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/media/00000000-0000-0000-0000-000000000000",
        headers=user_headers,
    )
    assert resp.status_code == 404


def test_update_media(client: TestClient, owner_headers: dict[str, str]) -> None:
    create = client.post(
        "/api/v1/media",
        json={"name": "Old Name"},
        headers=owner_headers,
    )
    mid = create.json()["id"]
    resp = client.patch(
        f"/api/v1/media/{mid}",
        json={"name": "New Name", "description": "Updated"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Updated"


def test_archive_media(
    client: TestClient, owner_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    create = client.post(
        "/api/v1/media",
        json={"name": "Disposable"},
        headers=owner_headers,
    )
    mid = create.json()["id"]
    resp = client.delete(f"/api/v1/media/{mid}", headers=owner_headers)
    assert resp.status_code == 204

    get_resp = client.get(f"/api/v1/media/{mid}", headers=user_headers)
    data = get_resp.json()
    assert data["is_archived"] is True


def test_media_response_shape(
    client: TestClient, owner_headers: dict[str, str], user_headers: dict[str, str]
) -> None:
    create = client.post(
        "/api/v1/media",
        json={"name": "Shape Test"},
        headers=owner_headers,
    )
    mid = create.json()["id"]
    resp = client.get(f"/api/v1/media/{mid}", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    expected_keys = {
        "id",
        "name",
        "description",
        "is_archived",
        "created_at",
        "updated_at",
    }
    assert set(data.keys()) == expected_keys
