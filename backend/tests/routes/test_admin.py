import uuid
from unittest.mock import MagicMock, patch

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


def test_list_users_requires_owner(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/admin/users", headers=user_headers)
    assert resp.status_code == 403

    resp = client.get("/api/v1/admin/users", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_update_user_role(client: TestClient, owner_headers: dict[str, str]) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "role-update@test.com",
            "password": "testpass123",
            "name": "Role Update",
        },
    )
    users = client.get("/api/v1/admin/users", headers=owner_headers).json()
    target = next(u for u in users if u["email"] == "role-update@test.com")
    resp = client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        json={"role": "owner"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


def test_audit_log(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/admin/audit-log", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


def test_dataowner_can_access_admin_users(
    client: TestClient,
) -> None:
    """Bug 005: dataowner role should have same admin access as owner."""
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "dataowner-test@mycoai.dev",
            "password": "password123",
            "name": "Data Owner Test",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    owner_token = login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    users = client.get("/api/v1/admin/users", headers=owner_headers).json()
    target = next(u for u in users if u["email"] == "dataowner-test@mycoai.dev")
    resp = client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        json={"role": "dataowner"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "dataowner"

    login2 = client.post(
        "/api/v1/auth/login",
        json={"email": "dataowner-test@mycoai.dev", "password": "password123"},
    )
    dataowner_token = login2.json()["access_token"]
    dataowner_headers = {"Authorization": f"Bearer {dataowner_token}"}

    resp = client.get("/api/v1/admin/users", headers=dataowner_headers)
    assert resp.status_code == 200, (
        f"dataowner should access admin users, got {resp.status_code}: {resp.text}"
    )


def test_invite_user(client: TestClient, owner_headers: dict[str, str]) -> None:
    """Bug 008: Invite user endpoint should work."""
    resp = client.post(
        "/api/v1/admin/users/invite",
        json={"email": "invited-user@mycoai.dev"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, (
        f"invite should succeed, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "invite_token" in data
    assert "invite_link" in data
    assert data["email"] == "invited-user@mycoai.dev"


def test_invite_user_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/admin/users/invite",
        json={"email": "nobody@mycoai.dev"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_register_with_invite_token(client: TestClient) -> None:
    """Bug 008: Register with invite token should work."""
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    owner_token = login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    invite = client.post(
        "/api/v1/admin/users/invite",
        json={"email": "token-register@mycoai.dev"},
        headers=owner_headers,
    )
    assert invite.status_code == 201
    token = invite.json()["invite_token"]

    resp = client.post(
        "/api/v1/auth/register-with-token",
        json={
            "email": "token-register@mycoai.dev",
            "token": token,
            "password": "securepass123",
            "name": "Token User",
        },
    )
    assert resp.status_code == 201, (
        f"register with token should succeed, got {resp.status_code}: {resp.text}"
    )
    data = resp.json()
    assert "access_token" in data


def test_register_with_invalid_token(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register-with-token",
        json={
            "email": "fake@mycoai.dev",
            "token": "invalid-token-12345",
            "password": "securepass123",
            "name": "Bad Token",
        },
    )
    assert resp.status_code in (401, 403), (
        f"expected 401/403 for bad token, got {resp.status_code}"
    )


def test_clear_test_data_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    """Bug 003: Clear test data should require owner."""
    resp = client.delete(
        "/api/v1/admin/test-data",
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_clear_test_data_deletes_matching_qdrant_points(
    client: TestClient, owner_headers: dict[str, str], session
) -> None:
    from backend.models import Image, Media, QdrantIndexState, Segment, Species, Strain

    species = Species(name="Spec A")
    media = Media(name="MEA")
    strain = Strain(name="TEST-001", species=species, source="test")
    image = Image(
        strain=strain,
        species=species,
        media=media,
        file_path="/tmp/test.jpg",
    )
    point_id = uuid.uuid4()
    segment = Segment(
        image=image,
        segment_index=0,
        crop_path="/tmp/crop.jpg",
        bbox_x=0,
        bbox_y=0,
        bbox_w=10,
        bbox_h=10,
        segmentation_method="kmeans",
        qdrant_point_id=point_id,
    )
    session.add_all(
        [
            species,
            media,
            strain,
            image,
            segment,
            QdrantIndexState(
                segment=segment,
                qdrant_point_id=point_id,
                collection_name="test-collection",
            ),
        ]
    )

    import asyncio

    asyncio.run(session.commit())
    fake_qdrant = MagicMock()

    with patch("backend.api.admin.get_qdrant_client", return_value=fake_qdrant):
        resp = client.delete(
            "/api/v1/admin/test-data?strain_pattern=TEST%25",
            headers=owner_headers,
        )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "deleted_strains": 1,
        "deleted_images": 1,
        "deleted_segments": 1,
    }
    fake_qdrant.delete.assert_called_once()
    _, kwargs = fake_qdrant.delete.call_args
    assert kwargs["collection_name"] == "test-collection"
    assert kwargs["points_selector"] == [point_id.int]
