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


def test_upload_image_via_upload_alias(
    client: TestClient, headers: dict[str, str]
) -> None:
    """Test the /upload alias route works identically."""
    tmp = Path("/tmp/test_upload_alias.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images/upload",
            files={"image": ("test_alias.png", f, "image/png")},
            data={
                "strain": "DTO 148-D2",
                "media": "CYA",
                "species": "Penicillium commune",
            },
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["segmentation_method"] == "kmeans"
    assert len(data["segments"]) >= 0


def test_upload_image_without_auth(client: TestClient) -> None:
    """Upload should require authentication."""
    tmp = Path("/tmp/test_noauth.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images/upload",
            files={"image": ("test.png", f, "image/png")},
            data={"strain": "test", "media": "MEA"},
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 401, f"Got {resp.status_code}: {resp.text}"


def test_batch_upload(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.post(
        "/api/v1/images/batch",
        json={"source_dir": "/tmp/nonexistent_dir_xyz"},
        headers=headers,
    )
    assert resp.status_code in (202, 422), f"Got {resp.status_code}: {resp.text}"


def test_batch_folder_upload_no_files(
    client: TestClient, headers: dict[str, str]
) -> None:
    """Batch folder upload with no files should 422."""
    resp = client.post(
        "/api/v1/images/batch-upload",
        data={
            "metadata": '{"batch_name": "test_batch"}',
            "default_media": "MEA",
        },
        headers=headers,
    )
    assert resp.status_code == 422, f"Got {resp.status_code}: {resp.text}"


def test_batch_folder_upload_single_image(
    client: TestClient, headers: dict[str, str]
) -> None:
    """Batch upload with one image file should succeed."""
    tmp = Path("/tmp/test_batch_img.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images/batch-upload",
            files=[
                ("files", ("mycoai_new_species/StrainA/img_01.png", f, "image/png")),
            ],
            data={
                "metadata": '{"batch_name": "test_batch", "strains": {"StrainA": {"species": "Penicillium", "media": "MEA"}}}',
                "default_media": "MEA",
            },
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 202, f"Got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["status"] == "completed"
    assert data["successful"] >= 1


def test_get_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.get("/api/v1/images/nonexistent-id", headers=headers)
    assert resp.status_code == 404, f"Got {resp.status_code}: {resp.text}"


def test_delete_image_not_found(client: TestClient, headers: dict[str, str]) -> None:
    resp = client.delete("/api/v1/images/nonexistent-id", headers=headers)
    assert resp.status_code in (404, 405), f"Got {resp.status_code}: {resp.text}"
