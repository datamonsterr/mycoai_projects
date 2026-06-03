from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import create_app

client = TestClient(create_app())


def test_router_exposes_protected_dashboard() -> None:
    resp = client.get("/api/v1/dashboard/stats")
    assert resp.status_code == 401


def test_auth_login_requires_payload() -> None:
    resp = client.post("/api/v1/auth/login")
    assert resp.status_code == 422


def test_health_endpoint_works() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
