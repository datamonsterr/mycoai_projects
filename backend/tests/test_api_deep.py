import pytest
from fastapi.testclient import TestClient


@pytest.fixture(name="user_headers")
def fixture_user_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@mycoai.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(name="owner_headers")
def fixture_owner_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(name="species_id")
def fixture_species_id(client: TestClient, owner_headers: dict[str, str]) -> str:
    resp = client.post(
        "/api/v1/species",
        json={"name": "Deep Test Species"},
        headers=owner_headers,
    )
    if resp.status_code == 409:
        list_resp = client.get("/api/v1/species", headers=owner_headers)
        for s in list_resp.json()["items"]:
            if s["name"] == "Deep Test Species":
                return s["id"]
    return resp.json()["id"]


# ── Health ───────────────────────────────────────────────────────────────────


def test_health_check(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "service" in data
    assert "environment" in data


def test_root_endpoint(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


# ── Auth / Register ──────────────────────────────────────────────────────────


def test_register_creates_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@mycoai.dev",
            "password": "testpass123",
            "name": "New User",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    email = "dup-test@mycoai.dev"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "First"},
    )
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "testpass123", "name": "Second"},
    )
    assert resp.status_code == 409


def test_register_rejects_short_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "shortpw@test.com", "password": "1234567", "name": "Short"},
    )
    assert resp.status_code == 422


def test_register_rejects_bad_email(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "12345678", "name": "Bad Email"},
    )
    assert resp.status_code == 422


# ── Auth / Login ─────────────────────────────────────────────────────────────


def test_login_returns_tokens(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_rejects_bad_password(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_login_rejects_nonexistent_user(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "noone@nowhere.com", "password": "password123"},
    )
    assert resp.status_code == 401


# ── Auth / Me ────────────────────────────────────────────────────────────────


def test_get_me_returns_user(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/auth/me", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "owner@mycoai.dev"
    assert data["role"] == "owner"
    assert data["name"] == "Owner"


def test_get_me_unauthorized_without_token(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_get_me_with_bad_token(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer garbage.token.here"},
    )
    assert resp.status_code == 401


def test_get_me_with_wrong_token_type(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    refresh_token = login_resp.json()["refresh_token"]
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert resp.status_code == 401


# ── Auth / Refresh & Logout ──────────────────────────────────────────────────


def test_refresh_returns_new_access_token(client: TestClient) -> None:
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    refresh_token = login.json()["refresh_token"]
    resp = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_logout_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "any"},
    )
    assert resp.status_code == 401


# ── Species CRUD ─────────────────────────────────────────────────────────────


def test_species_crud_as_owner(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    create = client.post(
        "/api/v1/species",
        json={"name": "Full CRUD Species", "description": "CRUD test"},
        headers=owner_headers,
    )
    assert create.status_code == 201
    sid = create.json()["id"]
    assert create.json()["name"] == "Full CRUD Species"

    get_resp = client.get(f"/api/v1/species/{sid}", headers=owner_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sid

    update = client.patch(
        f"/api/v1/species/{sid}",
        json={"name": "Updated CRUD Species"},
        headers=owner_headers,
    )
    assert update.status_code == 200
    assert update.json()["name"] == "Updated CRUD Species"

    delete = client.delete(f"/api/v1/species/{sid}", headers=owner_headers)
    assert delete.status_code == 204


def test_species_crud_forbidden_as_user(
    client: TestClient,
    user_headers: dict[str, str],
    owner_headers: dict[str, str],
) -> None:
    create = client.post(
        "/api/v1/species",
        json={"name": "Should Not Create"},
        headers=user_headers,
    )
    assert create.status_code == 403

    owner_create = client.post(
        "/api/v1/species",
        json={"name": "Owner Created"},
        headers=owner_headers,
    )
    sid = owner_create.json()["id"]

    patch_resp = client.patch(
        f"/api/v1/species/{sid}",
        json={"name": "User tries"},
        headers=user_headers,
    )
    assert patch_resp.status_code == 403

    delete_resp = client.delete(f"/api/v1/species/{sid}", headers=user_headers)
    assert delete_resp.status_code == 403


def test_species_list_with_pagination(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/species?offset=0&limit=5", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


# ── Strains CRUD ─────────────────────────────────────────────────────────────


def test_strains_create_requires_owner(
    client: TestClient,
    user_headers: dict[str, str],
    owner_headers: dict[str, str],
    species_id: str,
) -> None:
    payload = {"name": "Test Strain", "species_id": species_id}
    resp_user = client.post("/api/v1/strains", json=payload, headers=user_headers)
    assert resp_user.status_code == 403

    resp_owner = client.post("/api/v1/strains", json=payload, headers=owner_headers)
    assert resp_owner.status_code == 201
    assert resp_owner.json()["name"] == "Test Strain"


def test_strains_list_and_get(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/strains", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


def test_strains_get_not_found(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/strains/00000000-0000-0000-0000-000000000000",
        headers=user_headers,
    )
    assert resp.status_code == 404


# ── Images ───────────────────────────────────────────────────────────────────


def test_images_upload_requires_auth(client: TestClient) -> None:
    resp = client.post("/api/v1/images")
    assert resp.status_code == 401


def test_images_get_not_found(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/images/00000000-0000-0000-0000-000000000000", headers=owner_headers
    )
    assert resp.status_code == 404


def test_images_delete_not_found(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.delete(
        "/api/v1/images/00000000-0000-0000-0000-000000000000",
        headers=owner_headers,
    )
    assert resp.status_code == 404


# ── Feedback ─────────────────────────────────────────────────────────────────


def test_feedback_submit_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "Penicillium commune",
            "description": "test",
        },
    )
    assert resp.status_code == 401


def test_feedback_inbox_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/feedback/inbox", headers=user_headers)
    assert resp.status_code == 403


def test_feedback_update_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.patch(
        "/api/v1/feedback/some-id",
        json={"status": "accepted"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_feedback_batch_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/feedback/batch",
        json={"ids": ["id1"], "status": "accepted"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_feedback_crud_flow(
    client: TestClient,
    user_headers: dict[str, str],
    owner_headers: dict[str, str],
) -> None:
    submit = client.post(
        "/api/v1/feedback",
        json={
            "feedback_type": "wrong_prediction",
            "suggested_species": "Penicillium commune",
            "description": "Test feedback flow",
        },
        headers=user_headers,
    )
    assert submit.status_code == 201
    fid = submit.json()["id"]
    assert submit.json()["status"] == "pending"

    review = client.patch(
        f"/api/v1/feedback/{fid}",
        json={"status": "accepted", "review_note": "Correct"},
        headers=owner_headers,
    )
    assert review.status_code == 200
    assert review.json()["status"] == "accepted"


# ── Admin ────────────────────────────────────────────────────────────────────


def test_admin_users_list_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/admin/users", headers=user_headers)
    assert resp.status_code == 403


def test_admin_role_change_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.patch(
        "/api/v1/admin/users/some-id/role",
        json={"role": "owner"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_admin_users_list_as_owner(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/admin/users", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_admin_role_change_flow(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "role-target@test.com",
            "password": "testpass123",
            "name": "Target",
        },
    )
    users = client.get("/api/v1/admin/users", headers=owner_headers).json()
    target = next(u for u in users if u["email"] == "role-target@test.com")
    resp = client.patch(
        f"/api/v1/admin/users/{target['id']}/role",
        json={"role": "owner"},
        headers=owner_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "owner"


def test_admin_audit_log_accessible_by_any_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/admin/audit-log", headers=user_headers)
    assert resp.status_code == 200


# ── Dashboard ────────────────────────────────────────────────────────────────


def test_dashboard_stats_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 401


def test_dashboard_stats_as_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/dashboard/stats", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_species" in data
    assert "total_strains" in data
    assert "total_images" in data


def test_dashboard_charts_as_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    for route in [
        "/api/v1/dashboard/charts/species-distribution",
        "/api/v1/dashboard/charts/media-distribution",
        "/api/v1/dashboard/charts/timeline",
    ]:
        resp = client.get(route, headers=user_headers)
        assert resp.status_code == 200


def test_dashboard_qdrant_status_as_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/dashboard/qdrant-status", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "points_count" in data


# ── Retrieval ────────────────────────────────────────────────────────────────


def test_retrieval_query_requires_auth(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "fake-id",
            "k": 5,
            "aggregation": "weighted",
            "media_strategy": "E1",
        },
    )
    assert resp.status_code == 401


def test_retrieval_flow(client: TestClient, owner_headers: dict[str, str]) -> None:
    start = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": "00000000-0000-0000-0000-000000000000",
            "k": 3,
            "aggregation": "weighted",
            "media_strategy": "E1",
        },
        headers=owner_headers,
    )
    assert start.status_code == 404
    data = start.json()
    assert "detail" in data


def test_retrieval_job_not_found(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.get(
        "/api/v1/retrieval/jobs/00000000-0000-0000-0000-000000000000",
        headers=owner_headers,
    )
    assert resp.status_code == 404


def test_retrieval_query_sync(
    client: TestClient, owner_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/retrieval/query-sync",
        json={
            "image_id": "00000000-0000-0000-0000-000000000000",
            "k": 3,
            "aggregation": "avg",
            "media_strategy": "E2",
        },
        headers=owner_headers,
    )
    assert resp.status_code == 404


# ── Training ─────────────────────────────────────────────────────────────────


def test_training_status_as_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/training/status", headers=user_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "idle"


def test_training_trigger_requires_owner(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/v1/training/trigger",
        json={"reason": "test"},
        headers=user_headers,
    )
    assert resp.status_code == 403


def test_training_jobs_accessible_by_any_user(
    client: TestClient, user_headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/training/jobs", headers=user_headers)
    assert resp.status_code == 200


# ── Qdrant Search Router ─────────────────────────────────────────────────────


def test_qdrant_collections_stats(client: TestClient) -> None:
    resp = client.get("/api/collections/stats")
    assert resp.status_code in (200, 503)


def test_qdrant_media(client: TestClient) -> None:
    resp = client.get("/api/collections/media")
    assert resp.status_code in (200, 503)


# ── Error format ─────────────────────────────────────────────────────────────


def test_404_error_format(client: TestClient, owner_headers: dict[str, str]) -> None:
    resp = client.get(
        "/api/v1/species/00000000-0000-0000-0000-000000000000", headers=owner_headers
    )
    assert resp.status_code == 404
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/not-found"
    assert data["title"] == "Resource Not Found"
    assert data["status"] == 404


def test_401_error_format(client: TestClient) -> None:
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authentication"


def test_403_error_format(client: TestClient, user_headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/species",
        json={"name": "No Perm"},
        headers=user_headers,
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["type"] == "https://api.mycoai.dev/errors/authorization"


def test_422_error_format(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": "bad"},
    )
    assert resp.status_code == 422
