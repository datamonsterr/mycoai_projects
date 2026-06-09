from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mycoai_retrieval_backend.database import get_db
from mycoai_retrieval_backend.models import (
    Image,
    Media,
    RetrievalJob,
    RetrievalResult,
    Species,
    Strain,
    User,
)

pytestmark = [pytest.mark.integration, pytest.mark.integration_postgres]


def _token(user_id: str, role: str = "owner") -> str:
    from mycoai_retrieval_backend.core.security import create_access_token

    return create_access_token(user_id, role)


def _headers(user_id: str, role: str = "owner") -> dict[str, str]:
    return {"Authorization": f"Bearer {_token(user_id, role)}"}


async def _seed_user(pg_session: AsyncSession, email: str, role: str = "owner") -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed",
        name="API Test User",
        role=role,
        is_active=True,
    )
    pg_session.add(user)
    await pg_session.flush()
    return user


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def owner_user(pg_session: AsyncSession) -> User:
    return await _seed_user(pg_session, "api-owner@test.local", "owner")


@pytest_asyncio.fixture(scope="function")
async def normal_user(pg_session: AsyncSession) -> User:
    return await _seed_user(pg_session, "api-user@test.local", "user")


@pytest_asyncio.fixture(scope="function")
async def api_client(pg_session: AsyncSession) -> TestClient:
    from mycoai_retrieval_backend.app import create_app

    app = create_app()

    async def _override_get_db():
        yield pg_session

    app.dependency_overrides[get_db] = _override_get_db
    return TestClient(app)


# ── Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_register_login_refresh_flow(
    api_client: TestClient, pg_session: AsyncSession
) -> None:
    import bcrypt

    resp = api_client.post(
        "/api/v1/auth/register",
        json={
            "email": "flow@test.local",
            "password": "testpass123",
            "name": "Flow Tester",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    from mycoai_retrieval_backend.core.security import decode_access_token

    payload = decode_access_token(access_token)
    user_id = payload["sub"]

    existing = await pg_session.execute(select(User).where(User.id == user_id))
    if not existing.scalar_one_or_none():
        pg_session.add(
            User(
                id=user_id,
                email="flow@test.local",
                password_hash=bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode(),
                name="Flow Tester",
                role="user",
                is_active=True,
            )
        )
        await pg_session.flush()

    me_resp = api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "flow@test.local"

    refresh_resp = api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()

    logout_resp = api_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_resp.status_code == 204


@pytest.mark.asyncio
async def test_api_full_retrieval_flow_mocked(
    api_client: TestClient, owner_user: User
) -> None:
    headers = _headers(str(owner_user.id))

    resp = api_client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "fake-image-id",
            "k": 5,
            "aggregation": "weighted",
            "environment_strategy": "E1",
        },
        headers=headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    job_id = data["job_id"]

    status_resp = api_client.get(f"/api/v1/retrieval/jobs/{job_id}", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["job_id"] == job_id


@pytest.mark.asyncio
async def test_api_species_crud_full_cycle(
    api_client: TestClient, owner_user: User
) -> None:
    headers = _headers(str(owner_user.id))

    create = api_client.post(
        "/api/v1/species",
        json={"name": "CRUD Test Species", "description": "Created via API"},
        headers=headers,
    )
    assert create.status_code == 201
    created = create.json()
    assert created["name"] == "CRUD Test Species"
    sid = created["id"]

    get_resp = api_client.get(f"/api/v1/species/{sid}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "CRUD Test Species"

    list_resp = api_client.get("/api/v1/species", headers=headers)
    assert list_resp.status_code == 200
    assert "items" in list_resp.json()

    update = api_client.patch(
        f"/api/v1/species/{sid}",
        json={"name": "CRUD Updated", "description": "Modified"},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["name"] == "CRUD Updated"

    archive = api_client.delete(f"/api/v1/species/{sid}", headers=headers)
    assert archive.status_code == 204


@pytest.mark.asyncio
async def test_api_media_crud_full_cycle(
    api_client: TestClient,
    owner_user: User,
    pg_session: AsyncSession,
) -> None:
    media = Media(
        id=uuid.uuid4(),
        name="API Media Integration",
        description="Created",
    )
    pg_session.add(media)
    await pg_session.commit()

    loaded = (
        await pg_session.execute(
            select(Media).where(Media.name == "API Media Integration")
        )
    ).scalar_one()
    assert loaded.description == "Created"

    loaded.description = "Updated via ORM"
    await pg_session.commit()

    reloaded = (
        await pg_session.execute(
            select(Media).where(Media.name == "API Media Integration")
        )
    ).scalar_one()
    assert reloaded.description == "Updated via ORM"

    loaded.is_archived = True
    await pg_session.commit()

    archived = (
        await pg_session.execute(
            select(Media).where(Media.name == "API Media Integration")
        )
    ).scalar_one()
    assert archived.is_archived is True


@pytest.mark.asyncio
async def test_api_feedback_submit_review_cycle(
    api_client: TestClient,
    owner_user: User,
    normal_user: User,
    pg_session: AsyncSession,
) -> None:
    species = Species(name="Feedback Species", description="Test")
    pg_session.add(species)
    await pg_session.flush()

    strain = Strain(name="FS-001", species_id=species.id, source="user_upload")
    pg_session.add(strain)
    await pg_session.flush()

    media = Media(name="feedback-media", description="Media for feedback test")
    pg_session.add(media)
    await pg_session.flush()

    img = Image(
        id=uuid.uuid4(),
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path="feedback-test.jpg",
    )
    pg_session.add(img)
    await pg_session.flush()

    job = RetrievalJob(
        id=uuid.uuid4(),
        user_id=normal_user.id,
        job_type="single",
        config={"k": 5},
    )
    pg_session.add(job)
    await pg_session.flush()

    result = RetrievalResult(
        id=uuid.uuid4(),
        job_id=job.id,
        strain_name="FS-001",
        rank=1,
        species_name="Feedback Species",
        score=0.92,
    )
    pg_session.add(result)
    await pg_session.commit()

    user_headers = _headers(str(normal_user.id))
    submit = api_client.post(
        "/api/v1/feedback",
        json={
            "retrieval_result_id": str(result.id),
            "feedback_type": "wrong_prediction",
            "suggested_species": "Correct Species",
            "description": "Wrong prediction flagged",
        },
        headers=user_headers,
    )
    assert submit.status_code == 201
    sid = submit.json()["id"]
    assert submit.json()["status"] == "pending"

    owner_headers = _headers(str(owner_user.id), "owner")
    review = api_client.patch(
        f"/api/v1/feedback/{sid}",
        json={"status": "accepted", "review_note": "Good catch"},
        headers=owner_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "accepted"
    assert review.json()["review_note"] == "Good catch"


@pytest.mark.asyncio
async def test_api_rbac_enforcement(api_client: TestClient, normal_user: User) -> None:
    user_headers = _headers(str(normal_user.id), "user")

    resp = api_client.post(
        "/api/v1/species",
        json={"name": "RBAC Test", "description": "Should fail"},
        headers=user_headers,
    )
    assert resp.status_code == 403
