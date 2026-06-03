import pytest
from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(name="access_token")
def fixture_access_token(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    return resp.json()["access_token"]


def test_register_new_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "new@test.com", "password": "testpass123", "name": "New User"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


def test_register_duplicate_email_fails(client: TestClient) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "testpass123", "name": "Dup"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "dup@test.com", "password": "testpass123", "name": "Dup2"},
    )
    assert resp.status_code == 409


def test_login_success(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_login_bad_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


def test_refresh_token(client: TestClient) -> None:
    resp_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    refresh_token = resp_login.json()["refresh_token"]
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_get_me_authenticated(client: TestClient, access_token: str) -> None:
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "owner@mycoai.dev"
    assert data["role"] == "owner"


def test_get_me_unauthenticated(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_logout(client: TestClient, access_token: str) -> None:
    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "does-not-matter"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert resp.status_code == 204
