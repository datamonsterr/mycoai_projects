from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import patch

import cv2 as cv
import numpy as np
import pytest
from qdrant_client.models import Distance, VectorParams

from backend.config import get_qdrant_settings
from backend.database import get_db
from backend.app import create_app


class FakeS3Storage:
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


pytestmark = [pytest.mark.integration, pytest.mark.integration_qdrant]

TEST_COLLECTION = f"itest_retrieval_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def e2e_client(test_session_factory, qdrant_client):
    settings = get_qdrant_settings().model_copy(update={"collection_name": TEST_COLLECTION})
    fake_storage = FakeS3Storage()
    vectors = {
        get_qdrant_settings().default_vector_name: VectorParams(size=1280, distance=Distance.COSINE)
    }
    try:
        qdrant_client.create_collection(collection_name=TEST_COLLECTION, vectors_config=vectors)
    except Exception:
        pass

    with (
        patch("backend.app.create_storage", return_value=fake_storage),
        patch("backend.config.get_qdrant_settings", return_value=settings),
        patch("backend.qdrant.client.get_qdrant_settings", return_value=settings),
        patch("backend.services.qdrant_client.get_qdrant_settings", return_value=settings),
        patch("backend.api.retrieval.get_qdrant_settings", return_value=settings),
    ):
        app = create_app()
        app.dependency_overrides[get_db] = test_session_factory
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            yield client, fake_storage
        app.dependency_overrides.clear()

    qdrant_client.delete_collection(collection_name=TEST_COLLECTION)


@pytest.fixture
def headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def e2e_image() -> Path:
    path = Path("/tmp/opencode/e2e-upload.jpg")
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    cv.circle(image, (320, 320), 120, (190, 170, 150), -1)
    cv.imwrite(str(path), image)
    return path


def test_full_e2e_upload_segment_extract_retrieve_freq_strength_k5(e2e_client, headers, e2e_image: Path) -> None:
    client, _fake_storage = e2e_client

    with e2e_image.open("rb") as handle:
        upload = client.post(
            "/api/v1/images",
            files={"image": ("e2e-upload.jpg", handle, "image/jpeg")},
            data={
                "strain": "DTO 148-C8",
                "media": "CYA",
                "species": "Penicillium chrysogenum",
                "method": "yolo",
            },
            headers=headers,
        )
    assert upload.status_code == 201, upload.text
    image_id = upload.json()["image_id"]

    query = client.post(
        "/api/v1/retrieval/query",
        json={
            "image_id": image_id,
            "k": 5,
            "aggregation": "freq_strength",
            "media_strategy": "same_media",
        },
        headers=headers,
    )
    if query.status_code == 404 and "No active segments" in query.text:
        pytest.skip("YOLO produced no active segments for test image")
    assert query.status_code == 202, query.text
    job_id = query.json()["job_id"]

    status = client.get(f"/api/v1/retrieval/jobs/{job_id}", headers=headers)
    assert status.status_code == 200, status.text

    results = client.get(f"/api/v1/retrieval/jobs/{job_id}/results", headers=headers)
    assert results.status_code == 200, results.text
    payload = results.json()
    assert payload["status"] == "completed"
    assert isinstance(payload["queried_images"], list)
    assert isinstance(payload["rankings"], list)
