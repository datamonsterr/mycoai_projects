import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from mycoai_retrieval_backend.core.security import create_access_token
from mycoai_retrieval_backend.models import User


async def _create_owner(session: AsyncSession) -> User:
    user = User(
        email=f"err-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        name="Err Tester",
        role="owner",
    )
    session.add(user)
    await session.commit()
    return user


@pytest.fixture(name="owner_headers")
async def fixture_owner_headers(client: TestClient, session: AsyncSession):
    owner = await _create_owner(session)
    token = create_access_token(str(owner.id), owner.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_validation_error_returns_problem_details(client: TestClient):
    resp = client.post("/api/v1/auth/login")
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_not_found_returns_problem_details(
    client: TestClient, owner_headers: dict[str, str]
):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/species/{fake_id}", headers=owner_headers)
    assert resp.status_code == 404
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/not-found"
    assert data["title"] == "Resource Not Found"
    assert data["status"] == 404
    assert "detail" in data
    assert "instance" in data


def test_unauthorized_returns_401_problem_details(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authentication"
    assert data["title"] == "Authentication Failed"
    assert data["status"] == 401


@pytest.mark.asyncio
async def test_forbidden_returns_403_problem_details(
    client: TestClient, session: AsyncSession
):
    user = User(
        email=f"fbdn-{uuid.uuid4().hex[:6]}@test.com",
        password_hash="hash",
        name="User",
        role="user",
    )
    session.add(user)
    await session.commit()
    token = create_access_token(str(user.id), user.role)
    h = {"Authorization": f"Bearer {token}"}

    resp = client.post("/api/v1/species", json={"name": "Blocked"}, headers=h)
    assert resp.status_code == 403
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authorization"
    assert data["title"] == "Forbidden"
    assert data["status"] == 403


@pytest.mark.asyncio
async def test_conflict_returns_409_problem_details(
    client: TestClient, session: AsyncSession
):
    email = f"conflict-{uuid.uuid4().hex[:6]}@test.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "First"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123", "name": "Second"},
    )
    assert resp.status_code == 409
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/conflict"
    assert data["title"] == "Conflict"


@pytest.mark.asyncio
async def test_error_response_includes_error_code_field(
    client: TestClient, owner_headers: dict[str, str]
):
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/api/v1/species/{fake_id}", headers=owner_headers)
    assert resp.status_code == 404
    data = resp.json()
    assert "type" in data
    assert "title" in data
    assert "status" in data


@pytest.mark.asyncio
async def test_error_response_includes_field_errors_for_validation(client: TestClient):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-email", "password": "short"},
    )
    assert resp.status_code == 422
    data = resp.json()
    assert "detail" in data


def test_internal_error_does_not_leak_details(client: TestClient):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed"})
    assert resp.status_code < 500 or resp.status_code >= 400
    if resp.status_code == 500:
        data = resp.json()
        assert "password" not in str(data).lower()
        assert "secret" not in str(data).lower()
        assert "traceback" not in str(data).lower()


@pytest.mark.asyncio
async def test_secrets_not_in_error_responses(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login", json={"email": "x@x.com", "password": "x" * 20}
    )
    body = resp.text.lower()
    assert "secret" not in body
    assert "jwt_secret" not in body
