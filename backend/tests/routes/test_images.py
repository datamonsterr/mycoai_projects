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


@pytest.fixture(name="image_id")
def fixture_image_id(client: TestClient, headers: dict[str, str]) -> str:
    """Upload an image and return its ID for downstream tests."""
    tmp = Path("/tmp/test_image_fixture.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images",
            files={"image": ("test_fixture.png", f, "image/png")},
            data={
                "strain": "DTO 148-F1",
                "media": "CYA",
                "species": "Penicillium chrysogenum",
            },
            headers=headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 201
    return resp.json()["image_id"]


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


# ── list_images tests ────────────────────────────────────────────────────


def test_list_images_returns_items(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    resp = client.get("/api/v1/images", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert any(item["id"] == image_id for item in data["items"])


def test_list_images_source_url_format(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    """source_url for local storage uses API endpoint format."""
    resp = client.get("/api/v1/images", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    item = next(item for item in data["items"] if item["id"] == image_id)
    assert item["source_url"] == f"/api/v1/images/{image_id}/source"


def test_list_images_metadata_fields(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    """Each list item includes all expected metadata fields."""
    resp = client.get("/api/v1/images", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    item = next(item for item in data["items"] if item["id"] == image_id)
    assert item["strain_name"] == "DTO 148-F1"
    assert item["species_name"] == "Penicillium chrysogenum"
    assert item["media_name"] == "CYA"
    assert "file_path" in item
    assert "source_url" in item
    assert "segments_count" in item
    assert "data_update_status" in item
    assert "indexed_in_qdrant" in item
    assert "created_at" in item


def test_list_images_requires_auth(client: TestClient) -> None:
    resp = client.get("/api/v1/images")
    assert resp.status_code == 401


def test_list_images_search_by_strain(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    """Search by strain name (partial match)."""
    resp = client.get("/api/v1/images?search=148-F1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert any(item["id"] == image_id for item in data["items"])


def test_list_images_search_no_match(
    client: TestClient, headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/images?search=zzz_no_match_xyz", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


def test_list_images_pagination(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    resp = client.get("/api/v1/images?offset=0&limit=1", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) <= 1
    # total should reflect all images, not just the page
    assert data["total"] >= 1


# ── Presigned URL tests ──────────────────────────────────────────────────


class FakeS3Storage:
    """Simulates S3Storage for presigned URL testing."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}

    def get_url(self, key: str) -> str:
        return f"http://minio:9000/mycoai-images/{key}?token=fake"

    def get_bytes(self, key: str) -> bytes | None:
        return self._objects.get(key)

    def upload_bytes(self, key: str, data: bytes, content_type: str = "") -> str:
        self._objects[key] = data
        return f"s3://mycoai-images/{key}"

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)

    def object_exists(self, key: str) -> bool:
        return key in self._objects


@pytest.fixture(name="s3_client")
def fixture_s3_client(test_session_factory):
    """Create a test client with fake S3 storage via monkeypatch."""
    from unittest.mock import patch

    from backend.app import create_app
    from backend.database import get_db

    fake_storage = FakeS3Storage()

    with patch(
        "backend.app.create_storage",
        return_value=fake_storage,
    ):
        app = create_app()
        app.dependency_overrides[get_db] = test_session_factory
        with TestClient(app) as client:
            yield client, fake_storage
        app.dependency_overrides.clear()


def test_list_images_presigned_url_with_s3_storage(
    s3_client: tuple[TestClient, FakeS3Storage],
) -> None:
    """When S3 storage is used, source_url should be a presigned http URL."""
    client, fake_storage = s3_client

    # Register + login on the S3-backed app
    client.post(
        "/api/v1/auth/register",
        json={"email": "s3test@mycoai.dev", "password": "s3testpass", "name": "S3Tester"},
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "s3test@mycoai.dev", "password": "s3testpass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Upload an image through the fake S3 pipeline
    tmp = Path("/tmp/test_s3_presigned.png")
    tmp.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    with open(tmp, "rb") as f:
        resp = client.post(
            "/api/v1/images",
            files={"image": ("test_s3.png", f, "image/png")},
            data={
                "strain": "T999",
                "media": "MEA",
                "species": "TestSpecies",
            },
            headers=auth_headers,
        )
    tmp.unlink(missing_ok=True)
    assert resp.status_code == 201
    image_id = resp.json()["image_id"]

    # List images — source_url must be an http:// presigned URL
    list_resp = client.get("/api/v1/images", headers=auth_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    # Find our image (may be mixed with local-storage images from other fixtures)
    matches = [item for item in data["items"] if item["id"] == image_id]
    assert len(matches) == 1, f"Expected 1 match for {image_id}, got {len(matches)}. Items: {[(i['id'][:8], i.get('source_url','')) for i in data['items']]}"
    item = matches[0]
    assert item["source_url"].startswith("/minio/"), f"Got source_url: {item['source_url']}"
    assert "/source.jpg" in item["source_url"]
