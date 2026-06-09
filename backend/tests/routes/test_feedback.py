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


def test_list_my_feedback(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/feedback", headers=user_headers)
    assert resp.status_code == 200
    assert "items" in resp.json()


def test_feedback_inbox_accessible_by_any_authenticated_user(
    client: TestClient, user_headers: dict[str, str], owner_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/feedback/inbox", headers=user_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/feedback/inbox", headers=owner_headers)
    assert resp.status_code == 200


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
    fid1 = r1.json()["id"]
    fid2 = r2.json()["id"]
    resp = client.post(
        "/api/v1/feedback/batch",
        json={"feedback_ids": [fid1, fid2], "status": "rejected"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 2
