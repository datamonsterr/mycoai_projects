from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
from uuid import UUID

import cv2 as cv
import numpy as np
import pytest
from sqlalchemy import select

from backend.app import create_app
from backend.database import get_db
from backend.models import Image, QdrantIndexState, Segment


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


@pytest.fixture
def s3_client(test_session_factory):
    fake_storage = FakeS3Storage()
    with patch("backend.app.create_storage", return_value=fake_storage):
        app = create_app()
        app.dependency_overrides[get_db] = test_session_factory
        from fastapi.testclient import TestClient

        with TestClient(app) as client:
            yield client, fake_storage
        app.dependency_overrides.clear()


@pytest.fixture
def image_file() -> Path:
    path = Path("/tmp/opencode/integration-upload.jpg")
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    cv.circle(image, (280, 280), 110, (180, 160, 140), -1)
    cv.imwrite(str(path), image)
    return path


@pytest.fixture
def headers(client):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_upload_image_persists_db_qdrant_and_storage(
    s3_client, headers, image_file: Path, session
) -> None:
    client, fake_storage = s3_client
    with image_file.open("rb") as handle:
        response = client.post(
            "/api/v1/images",
            files={"image": ("integration-upload.jpg", handle, "image/jpeg")},
            data={
                "strain": "DTO 148-C8",
                "media": "CYA",
                "species": "Penicillium chrysogenum",
                "method": "yolo",
            },
            headers=headers,
        )

    assert response.status_code == 201, response.text
    image_id = UUID(response.json()["image_id"])

    image_row = (
        await session.execute(select(Image).where(Image.id == image_id))
    ).scalar_one()
    segments = (
        (await session.execute(select(Segment).where(Segment.image_id == image_id)))
        .scalars()
        .all()
    )
    index_states = (
        (
            await session.execute(
                select(QdrantIndexState).where(
                    QdrantIndexState.segment_id.in_(
                        [segment.id for segment in segments]
                    )
                )
            )
        )
        .scalars()
        .all()
        if segments
        else []
    )

    assert image_row.file_path
    assert image_row.media_id is not None
    assert any(key.endswith("source.jpg") for key in fake_storage._objects)
    if segments:
        assert len(index_states) == len(
            [segment for segment in segments if segment.qdrant_point_id is not None]
        )
