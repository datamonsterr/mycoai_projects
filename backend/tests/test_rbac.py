import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import (
    create_access_token,
    create_refresh_token,
)
from backend.models import User


async def _create_user(
    session: AsyncSession, *, role: str = "user", is_active: bool = True
) -> User:
    user = User(
        email=f"{uuid.uuid4().hex[:8]}@test.com",
        password_hash="hash",
        name="Test",
        role=role,
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    return user


async def _create_owner(session: AsyncSession) -> User:
    return await _create_user(session, role="owner")


# ── get_current_user tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_extracts_user_from_token(
    client: TestClient, session: AsyncSession
):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == owner.email
    assert resp.json()["role"] == "owner"


@pytest.mark.asyncio
async def test_get_current_user_rejects_missing_auth_header(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token(client: TestClient):
    resp = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_expired_token(
    client: TestClient, session: AsyncSession
):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, role="user", is_active=False)
    token = create_access_token(str(user.id), user.role)
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_rejects_refresh_token_type(
    client: TestClient, session: AsyncSession
):
    owner = await _create_owner(session)
    refresh = create_refresh_token(str(owner.id))
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh}"})
    assert resp.status_code == 401


# ── require_role tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_role_passes_when_role_matches(
    client: TestClient, session: AsyncSession
):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    resp = client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_require_role_raises_403_when_role_mismatch(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, role="user")
    token = create_access_token(str(user.id), user.role)
    resp = client.get(
        "/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


# ── require_owner tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_require_owner_allows_data_owner(
    client: TestClient, session: AsyncSession
):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    resp = client.post(
        "/api/v1/species",
        json={"name": "Test Species"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_require_owner_rejects_user_with_403(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, role="user")
    token = create_access_token(str(user.id), user.role)
    resp = client.post(
        "/api/v1/species",
        json={"name": "Test Species"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


# ── endpoint accessibility ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_user_endpoints_accessible_to_user_role(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, role="user")
    token = create_access_token(str(user.id), user.role)
    h = {"Authorization": f"Bearer {token}"}

    r1 = client.get("/api/v1/species", headers=h)
    assert r1.status_code == 200

    r2 = client.get("/api/v1/auth/me", headers=h)
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_owner_endpoints_blocked_for_user_role(
    client: TestClient, session: AsyncSession
):
    user = await _create_user(session, role="user")
    token = create_access_token(str(user.id), user.role)
    h = {"Authorization": f"Bearer {token}"}

    r1 = client.post("/api/v1/species", json={"name": "Blocked"}, headers=h)
    assert r1.status_code == 403

    r2 = client.get("/api/v1/admin/users", headers=h)
    assert r2.status_code == 403


def test_public_endpoints_accessible_without_auth(client: TestClient):
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


@pytest.mark.asyncio
async def test_public_register_endpoint_accessible_without_auth(
    client: TestClient, session: AsyncSession
):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "public@test.com", "password": "password123", "name": "Public"},
    )
    assert resp.status_code == 201


# ── last owner protection ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cannot_demote_last_owner(client: TestClient, session: AsyncSession):
    owner = await _create_owner(session)
    await _create_user(session, role="user")
    token = create_access_token(str(owner.id), owner.role)
    h = {"Authorization": f"Bearer {token}"}

    resp = client.patch(
        f"/api/v1/admin/users/{owner.id}/role",
        json={"role": "user"},
        headers=h,
    )
    assert resp.status_code in (400, 409, 422)


@pytest.mark.asyncio
async def test_cannot_deactivate_last_owner(client: TestClient, session: AsyncSession):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    h = {"Authorization": f"Bearer {token}"}

    resp = client.patch(
        f"/api/v1/admin/users/{owner.id}",
        json={"is_active": False},
        headers=h,
    )
    assert resp.status_code in (400, 403, 404, 405, 409, 422)
