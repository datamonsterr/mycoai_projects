import pytest
from fastapi.testclient import TestClient


@pytest.fixture(name="owner_headers")
def fixture_owner_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_media_trash_restore_and_clean(
    client: TestClient,
    owner_headers: dict[str, str],
) -> None:
    create = client.post(
        "/api/v1/media",
        json={"name": "TRASH_MEDIA"},
        headers=owner_headers,
    )
    media_id = create.json()["id"]

    archive = client.delete(f"/api/v1/media/{media_id}", headers=owner_headers)
    assert archive.status_code == 204

    archived_list = client.get("/api/v1/media?is_archived=true", headers=owner_headers)
    assert archived_list.status_code == 200
    assert any(item["id"] == media_id for item in archived_list.json()["items"])

    restore = client.post(f"/api/v1/media/{media_id}/restore", headers=owner_headers)
    assert restore.status_code == 200
    assert restore.json()["is_archived"] is False

    client.delete(f"/api/v1/media/{media_id}", headers=owner_headers)
    clean = client.delete(f"/api/v1/media/{media_id}/clean", headers=owner_headers)
    assert clean.status_code == 204

    missing = client.get(f"/api/v1/media/{media_id}", headers=owner_headers)
    assert missing.status_code == 404
