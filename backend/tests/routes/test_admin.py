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
