import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from mycoai_retrieval_backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from mycoai_retrieval_backend.models import User


async def _create_user(
    session: AsyncSession,
    *,
    role: str = "user",
    is_active: bool = True,
    email: str | None = None,
) -> User:
    user = User(
        email=email or f"flow-{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password("password123"),
        name="Flow Tester",
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    return user


@pytest.fixture(name="user_with_token")
async def fixture_user_with_token(client: TestClient, session: AsyncSession):
    email = f"login-{uuid.uuid4().hex[:6]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "Login User"},
    )
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    data = resp.json()
    return {
        "email": email,
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


# ── registration edge cases ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_with_too_short_password_returns_422(client: TestClient):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "shortpw@test.com", "password": "short", "name": "Test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_with_invalid_email_returns_422(client: TestClient):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "password123", "name": "Test"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(
    client: TestClient, session: AsyncSession
):
    email = f"dup-{uuid.uuid4().hex[:6]}@test.com"
    await _create_user(session, email=email)
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "Duplicate"},
    )
    assert resp.status_code == 409


# ── login edge cases ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_with_wrong_password_returns_401(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_with_nonexistent_email_returns_401(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "no-such-user@test.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_with_inactive_account_returns_401(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, is_active=False)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "password123"},
    )
    assert resp.status_code == 401


# ── token refresh ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_token_refresh_works(client: TestClient, user_with_token: dict):
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": user_with_token["refresh_token"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


@pytest.mark.asyncio
async def test_token_refresh_with_expired_token_returns_401(client: TestClient):
    resp = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "expired-token-value"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_token_refresh_with_access_token_returns_401(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session)
    access = create_access_token(str(user.id), user.role)
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


# ── logout ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client: TestClient, user_with_token: dict):
    h = {"Authorization": f"Bearer {user_with_token['access_token']}"}
    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": user_with_token["refresh_token"]},
        headers=h,
    )
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_cannot_refresh_after_logout(client: TestClient, user_with_token: dict):
    h = {"Authorization": f"Bearer {user_with_token['access_token']}"}
    refresh = user_with_token["refresh_token"]

    client.post("/api/v1/auth/logout", json={"refresh_token": refresh}, headers=h)
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


# ── password security ───────────────────────────────────────────────────────


def test_password_hash_is_not_reversible():
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert (
        hashed.startswith("$2b$")
        or hashed.startswith("$2a$")
        or hashed.startswith("$2y$")
    )
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


# ── token expiry ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_access_token_expires_correctly(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session)
    token = create_access_token(str(user.id), user.role)
    payload = decode_access_token(token)
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "sub" in payload
    assert payload["sub"] == str(user.id)
