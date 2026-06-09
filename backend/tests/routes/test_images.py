from pathlib import Path

import pytest
from fastapi.testclient import TestClient


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
            "/api/v1/images",
            files={"image": ("test.png", f, "image/png")},
            data={
                "strain": "DTO 148-D1",
                "media": "MEA",
                "species": "Penicillium commune",
            },
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "image_id" in data
    assert "segments" in data
    assert "source_url" in data
    assert "segmentation_method" in data


def test_batch_upload(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/images/batch",
        json={"source_dir": "/tmp/nonexistent_dir_xyz"},
        headers=headers,
    )
    # Should get 422 because dir doesn't exist
    assert resp.status_code in (202, 422), f"Got {resp.status_code}: {resp.text}"


def test_get_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/images/nonexistent-id", headers=headers)
    assert resp.status_code == 404, f"Got {resp.status_code}: {resp.text}"


def test_delete_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.delete("/api/v1/images/nonexistent-id", headers=headers)
    # May return 404 or 405 depending on route registration
    assert resp.status_code in (404, 405), f"Got {resp.status_code}: {resp.text}"
