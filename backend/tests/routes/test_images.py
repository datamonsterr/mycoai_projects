from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import app


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(app)


@pytest.fixture(name="headers")
def fixture_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_upload_image(client: TestClient, headers: dict[str, str]) -> None:
    tmp = Path("/tmp/test_upload.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images/upload",
            files={"image": ("test.png", f, "image/png")},
            data={"strain": "DTO 148-D1", "media": "MEA"},
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending_segmentation"
    assert data["strain"] == "DTO 148-D1"
    assert data["media"] == "MEA"
    assert "image_id" in data
    assert "job_id" in data


def test_batch_upload(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post("/api/v1/images/batch", headers=headers)
    assert resp.status_code == 202
    assert "job_id" in resp.json()


def test_get_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/images/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_delete_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.delete("/api/v1/images/nonexistent", headers=headers)
    assert resp.status_code == 404


def test_list_segments_empty(client: TestClient, headers: dict[str, str]) -> None:
    tmp = Path("/tmp/test_seg.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images/upload",
            files={"image": ("segtest.png", f, "image/png")},
            data={"strain": "DTO 148-D1", "media": "MEA"},
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    image_id = resp.json()["image_id"]
    r = client.get(f"/api/v1/images/{image_id}/segments", headers=headers)
    assert r.status_code == 200
    assert r.json() == []
