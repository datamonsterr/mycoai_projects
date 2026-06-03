from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import create_app

client = TestClient(create_app())


def test_404_returns_problem_json() -> None:
    resp = client.get("/nonexistent")
    assert resp.status_code == 404
    data = resp.json()
    assert data["title"] == "Not Found"
    assert data["status"] == 404
