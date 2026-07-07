import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Image, Media, Species, Strain, SystemState


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


async def _seed_image(session: AsyncSession, name: str = "Feedback Species") -> Image:
    species = Species(name=name)
    session.add(species)
    await session.flush()
    strain = Strain(name=f"{name}-strain", species_id=species.id, source="user_upload")
    media = Media(name=f"{name}-media")
    session.add_all([strain, media])
    await session.flush()
    image = Image(
        strain_id=strain.id,
        species_id=species.id,
        media_id=media.id,
        file_path=f"images/{name}.jpg",
    )
    session.add(image)
    await session.commit()
    return image


async def _images_added(session: AsyncSession) -> int:
    result = await session.execute(
        select(SystemState).where(SystemState.key == "retraining_counter")
    )
    row = result.scalar_one_or_none()
    if row is None:
        return 0
    return int(row.value.get("images_added", 0))


def test_submit_feedback(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "Penicillium commune",
            "description": "Looks correct",
        },
        headers=user_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["suggested_species"] == "Penicillium commune"
    assert resp.json()["status"] == "pending"
    assert resp.json()["source"] == "retrieval_result"


def test_rejects_bad_image_id(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "image_id": "not-a-uuid",
            "suggested_species": "Penicillium commune",
            "description": "bad image id",
        },
        headers=user_headers,
    )
    assert resp.status_code == 422


def test_rejects_empty_suggested_species(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "",
            "description": "empty species",
        },
        headers=user_headers,
    )
    assert resp.status_code == 422


def test_list_my_feedback(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/feedback", headers=user_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_feedback_inbox_requires_owner(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/feedback/inbox", headers=user_headers)
    assert resp.status_code == 403

    resp = client.get("/api/v1/feedback/inbox", headers=owner_headers)
    assert resp.status_code == 200


def test_user_cannot_review_feedback(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/v1/feedback",
        json={"feedback_type": "issue", "description": "test"},
        headers=owner_headers,
    )
    resp = client.patch(
        f"/api/v1/feedback/{created.json()['id']}",
        json={"status": "accepted"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_user_cannot_batch_review(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/feedback/batch",
        json={"feedback_ids": [], "status": "accepted"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_review_feedback(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "Penicillium commune",
            "description": "test",
        },
        headers=owner_headers,
    )
    fid = resp.json()["id"]
    review = client.patch(
        f"/api/v1/feedback/{fid}",
        json={"status": "accepted", "review_note": "good"},
        headers=owner_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "accepted"
    assert review.json()["reviewer_id"] is not None


@pytest.mark.asyncio
async def test_list_my_feedback_visibility_scoped_to_submitter(
    client: TestClient,
    session: AsyncSession,
    owner_headers: dict[str, str],
    user_headers: dict[str, str],
) -> None:
    client.post(
        "/api/v1/feedback",
        json={"feedback_type": "issue", "description": "owner-only"},
        headers=owner_headers,
    )
    result = await session.execute(select(SystemState))
    assert result.scalars().all() == []
    resp = client.get("/api/v1/feedback", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["items"] == []


@pytest.mark.asyncio
async def test_accept_contribution_marks_reference_and_counts(
    client: TestClient,
    session: AsyncSession,
    owner_headers: dict[str, str],
) -> None:
    image = await _seed_image(session, "Contribution Species")
    before = await _images_added(session)
    created = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "contribution",
            "image_id": str(image.id),
            "predicted_species": "Contribution Species",
            "description": "correct prediction",
        },
        headers=owner_headers,
    )
    review = client.patch(
        f"/api/v1/feedback/{created.json()['id']}",
        json={"status": "accepted"},
        headers=owner_headers,
    )
    await session.refresh(image)
    assert review.status_code == 200
    assert review.json()["predicted_species"] == "Contribution Species"
    assert image.data_update_status == "pending_reference"
    assert await _images_added(session) == before + 1


@pytest.mark.asyncio
async def test_accept_wrong_prediction_marks_reindex_without_counting(
    client: TestClient,
    session: AsyncSession,
    owner_headers: dict[str, str],
) -> None:
    image = await _seed_image(session, "Wrong Prediction Species")
    before = await _images_added(session)
    created = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "image_id": str(image.id),
            "predicted_species": "Predicted Species",
            "suggested_species": "Correct Species",
            "description": "wrong prediction",
        },
        headers=owner_headers,
    )
    review = client.patch(
        f"/api/v1/feedback/{created.json()['id']}",
        json={"status": "accepted"},
        headers=owner_headers,
    )
    await session.refresh(image)
    assert review.status_code == 200
    assert image.data_update_status == "pending_reindex"
    assert await _images_added(session) == before


def test_batch_feedback(client: TestClient, owner_headers: dict[str, str]) -> None:
    r1 = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "P. commune",
            "description": "d1",
        },
        headers=owner_headers,
    )
    r2 = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "P. commune",
            "description": "d2",
        },
        headers=owner_headers,
    )
    resp = client.post(
        "/api/v1/feedback/batch",
        json={"feedback_ids": [r1.json()["id"], r2.json()["id"]], "status": "rejected"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2


def test_batch_feedback_counts_only_existing(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/feedback/batch",
        json={
            "feedback_ids": ["00000000-0000-0000-0000-000000000000"],
            "status": "rejected",
        },
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 0
