from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app

client = TestClient(app)


def test_healthcheck_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_exposes_key_endpoints() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "MycoAI Retrieval Backend",
        "docs": "/docs",
        "health": "/health",
    }
