import asyncio
from pathlib import Path
from uuid import UUID, uuid4

import cv2 as cv
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.config import get_qdrant_settings
from backend.models import Image, Media, QdrantIndexState, Segment, Species, Strain
from backend.services.feature_extraction import index_segment_to_qdrant


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
                "metadata": (
                    '{"batch_name": "test_batch", "strains": '
                    '{"StrainA": {"species": "Penicillium", "media": "MEA"}}}'
                ),
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


def test_list_image_groups_returns_strain_rows(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    resp = client.get("/api/v1/images/groups", headers=headers)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    group = data["items"][0]
    assert group["strain_name"] == "DTO 148-F1"
    assert group["species_name"] == "Penicillium chrysogenum"
    assert group["media_names"] == ["CYA"]
    assert group["image_count"] == 1
    assert group["images"][0]["id"] == image_id
    assert "segments_count" not in group["images"][0]


def test_list_image_groups_filters_child_images(
    client: TestClient, headers: dict[str, str], image_id: str
) -> None:
    resp = client.get(
        "/api/v1/images/groups?search=148-F1&status=current",
        headers=headers,
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert [image["id"] for image in data["items"][0]["images"]] == [image_id]


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


def _login_s3_test_user(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "s3test@mycoai.dev",
            "password": "s3testpass",
            "name": "S3Tester",
        },
    )
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "s3test@mycoai.dev", "password": "s3testpass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_s3_test_image(client: TestClient, auth_headers: dict[str, str]) -> str:
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
    return resp.json()["image_id"]


def test_list_images_presigned_url_with_s3_storage(
    s3_client: tuple[TestClient, FakeS3Storage],
) -> None:
    """When S3 storage is used, source_url should be a presigned http URL."""
    client, fake_storage = s3_client
    auth_headers = _login_s3_test_user(client)
    image_id = _upload_s3_test_image(client, auth_headers)

    list_resp = client.get("/api/v1/images", headers=auth_headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    matches = [item for item in data["items"] if item["id"] == image_id]
    assert len(matches) == 1, (
        f"Expected 1 match for {image_id}, got {len(matches)}. "
        f"Items: {[(i['id'][:8], i.get('source_url', '')) for i in data['items']]}"
    )
    item = matches[0]
    assert item["source_url"].startswith("/minio/"), (
        f"Got source_url: {item['source_url']}"
    )
    assert "/source.jpg" in item["source_url"]


def test_auto_segment_after_s3_upload_reuses_uploaded_source(
    s3_client: tuple[TestClient, FakeS3Storage],
) -> None:
    client, _fake_storage = s3_client
    auth_headers = _login_s3_test_user(client)
    image_id = _upload_s3_test_image(client, auth_headers)

    resp = client.post(
        f"/api/v1/images/{image_id}/segment",
        json={"method": "kmeans"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["image_id"] == image_id


@pytest.fixture(name="sample_source_png")
def fixture_sample_source_png() -> bytes:
    image = np.full((4, 4, 3), 255, dtype=np.uint8)
    ok, encoded = cv.imencode(".png", image)
    assert ok
    return encoded.tobytes()


@pytest.fixture(name="user_headers")
def fixture_user_headers(client: TestClient) -> dict[str, str]:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "user@mycoai.dev", "password": "password123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="db_image_id")
def fixture_db_image_id(session, sample_source_png: bytes) -> str:
    async def seed() -> str:
        tmp = Path("/tmp/opencode/test_db_image_source.png")
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_bytes(sample_source_png)

        species = Species(name="Patch Species")
        media = Media(name="PATCH_MEDIA")
        strain = Strain(name="PATCH_STRAIN", species=species, source="test")
        image = Image(
            strain=strain,
            species=species,
            media=media,
            file_path=str(tmp),
            prepared_path=str(tmp),
            pipeline_path=str(tmp),
            data_update_status="current",
        )
        crop_path = Path("/tmp/opencode/test_db_image_segment_0.jpg")
        crop_path.write_bytes(sample_source_png)
        segment = Segment(
            image=image,
            segment_index=0,
            crop_path=str(crop_path),
            bbox_x=0,
            bbox_y=0,
            bbox_w=2,
            bbox_h=2,
            segmentation_method="kmeans",
            qdrant_point_id=uuid4(),
        )
        session.add_all([species, media, strain, image, segment])
        await session.commit()
        return str(image.id)

    return asyncio.run(seed())


def test_patch_segments_persists_db_and_clears_index_state(
    client: TestClient,
    headers: dict[str, str],
    db_image_id: str,
    monkeypatch: pytest.MonkeyPatch,
    session,
) -> None:
    point_id = uuid4()

    async def seed_qdrant_state() -> UUID:
        segment_id = await session.scalar(
            select(Segment.id).join(Image).where(Image.id == UUID(db_image_id))
        )
        assert segment_id is not None
        session.add(
            QdrantIndexState(
                segment_id=segment_id,
                qdrant_point_id=point_id,
                collection_name="test_collection",
                is_active=True,
            )
        )
        await session.commit()
        return segment_id

    asyncio.run(seed_qdrant_state())

    deleted: list[tuple[list[int], str | None]] = []

    def fake_delete_points(client_obj, point_ids, collection_name=None):
        deleted.append((list(point_ids), collection_name))
        return len(point_ids)

    monkeypatch.setattr("backend.routes.delete_points", fake_delete_points)
    monkeypatch.setattr(
        "backend.routes.get_qdrant_client", lambda: object(), raising=False
    )

    resp = client.patch(
        f"/api/v1/images/{db_image_id}/segments",
        json={
            "segments": [{"segment_index": 0, "bbox": {"x": 0, "y": 0, "w": 1, "h": 1}}]
        },
        headers=headers,
    )

    assert resp.status_code == 200, resp.text

    async def fetch_state() -> tuple[
        Image | None, Segment | None, QdrantIndexState | None
    ]:
        await session.rollback()
        refreshed = await session.scalar(
            select(Image).where(Image.id == UUID(db_image_id))
        )
        seg = None
        state = None
        if refreshed is not None:
            await session.refresh(refreshed)
            seg = await session.scalar(
                select(Segment).where(Segment.image_id == refreshed.id)
            )
            if seg is not None:
                await session.refresh(seg)
                state = await session.scalar(
                    select(QdrantIndexState).where(
                        QdrantIndexState.segment_id == seg.id
                    )
                )
        return refreshed, seg, state

    refreshed, seg, state = asyncio.run(fetch_state())
    assert refreshed is not None
    assert refreshed.data_update_status == "updated_requires_reindex"
    assert seg is not None
    assert (seg.bbox_x, seg.bbox_y, seg.bbox_w, seg.bbox_h) == (0, 0, 1, 1)
    assert seg.qdrant_point_id is None
    assert state is None
    assert deleted == [([point_id.int], "test_collection")]


def test_patch_segments_allowed_for_regular_authenticated_user(
    client: TestClient,
    user_headers: dict[str, str],
    db_image_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("backend.routes.delete_points", lambda *args, **kwargs: 0)
    monkeypatch.setattr(
        "backend.routes.get_qdrant_client", lambda: object(), raising=False
    )

    resp = client.patch(
        f"/api/v1/images/{db_image_id}/segments",
        json={
            "segments": [{"segment_index": 0, "bbox": {"x": 0, "y": 0, "w": 1, "h": 1}}]
        },
        headers=user_headers,
    )

    assert resp.status_code == 200, resp.text


def test_reextract_one_image_endpoint_reindexes_segments(
    client: TestClient,
    headers: dict[str, str],
    db_image_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    async def fake_index_segment_to_qdrant(db, segment, image_obj, **kwargs):
        calls.append(segment.segment_index)
        segment.qdrant_point_id = uuid4()
        return {"status": "indexed"}

    monkeypatch.setattr(
        "backend.routes.index_segment_to_qdrant", fake_index_segment_to_qdrant
    )

    resp = client.post(
        f"/api/v1/images/{db_image_id}/reindex",
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    assert calls == [0]
    body = resp.json()
    assert body["image_id"] == db_image_id
    assert body["indexed_segments"] == 1


def test_reextract_batch_strain_endpoint_reindexes_eligible_images(
    client: TestClient,
    headers: dict[str, str],
    sample_source_png: bytes,
    monkeypatch: pytest.MonkeyPatch,
    session,
) -> None:
    tmp_root = Path("/tmp/opencode/reindex_batch")
    tmp_root.mkdir(parents=True, exist_ok=True)

    async def seed_batch() -> tuple[str, list[str]]:
        species = Species(name="Batch Species")
        media = Media(name="BATCH_MEDIA")
        strain = Strain(name="BATCH_STRAIN", species=species, source="test")
        session.add_all([species, media, strain])
        await session.commit()

        image_ids: list[str] = []
        for idx in range(2):
            source_path = tmp_root / f"source_{idx}.png"
            source_path.write_bytes(sample_source_png)
            crop_path = tmp_root / f"segment_{idx}.jpg"
            crop_path.write_bytes(sample_source_png)
            image = Image(
                strain_id=strain.id,
                species_id=species.id,
                media_id=media.id,
                file_path=str(source_path),
                prepared_path=str(source_path),
                pipeline_path=str(source_path),
                data_update_status="updated_requires_reindex",
            )
            session.add(image)
            await session.flush()
            session.add(
                Segment(
                    image_id=image.id,
                    segment_index=0,
                    crop_path=str(crop_path),
                    bbox_x=0,
                    bbox_y=0,
                    bbox_w=2,
                    bbox_h=2,
                    segmentation_method="kmeans",
                )
            )
            image_ids.append(str(image.id))
        await session.commit()
        return str(strain.id), image_ids

    strain_id, image_ids = asyncio.run(seed_batch())

    calls: list[str] = []

    async def fake_index_segment_to_qdrant(db, segment, image_obj, **kwargs):
        calls.append(str(image_obj.id))
        segment.qdrant_point_id = uuid4()
        return {"status": "indexed"}

    monkeypatch.setattr(
        "backend.routes.index_segment_to_qdrant", fake_index_segment_to_qdrant
    )

    resp = client.post(
        f"/api/v1/images/strains/{strain_id}/reindex",
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    assert sorted(calls) == sorted(image_ids)
    body = resp.json()
    assert body["strain_id"] == strain_id
    assert body["images"] == 2
    assert body["indexed_segments"] == 2


class _RecordingStorage:
    def __init__(self, objects: dict[str, bytes]) -> None:
        self.objects = objects
        self.calls: list[str] = []

    def upload_bytes(
        self, key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        self.objects[key] = data
        return f"s3://bucket/{key}"

    def get_url(self, key: str) -> str:
        return f"https://example.invalid/{key}"

    def get_bytes(self, key: str) -> bytes | None:
        self.calls.append(key)
        return self.objects.get(key)

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def object_exists(self, key: str) -> bool:
        return key in self.objects


def test_index_segment_to_qdrant_uses_configured_collection_name(
    session,
    sample_source_png: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tmp_root = Path("/tmp/opencode/reindex_collection")
    tmp_root.mkdir(parents=True, exist_ok=True)

    async def seed() -> tuple[Segment, Image]:
        species = Species(name="Cfg Species")
        media = Media(name="CFG_MEDIA")
        strain = Strain(name="CFG_STRAIN", species=species, source="test")
        session.add_all([species, media, strain])
        await session.flush()

        source_path = tmp_root / "source.png"
        source_path.write_bytes(sample_source_png)
        crop_path = tmp_root / "segment_0.jpg"
        crop_path.write_bytes(sample_source_png)
        image = Image(
            strain_id=strain.id,
            species_id=species.id,
            media_id=media.id,
            file_path=str(source_path),
            prepared_path=str(source_path),
            pipeline_path=str(source_path),
        )
        session.add(image)
        await session.flush()
        segment = Segment(
            image_id=image.id,
            segment_index=0,
            crop_path=str(crop_path),
            bbox_x=1,
            bbox_y=2,
            bbox_w=3,
            bbox_h=4,
            segmentation_method="kmeans",
        )
        session.add(segment)
        await session.flush()
        return segment, image

    segment, image = asyncio.run(seed())
    collection_name = "qdrant-research_fold0"

    class _FakeClient:
        def get_collection(
            self, requested_collection_name: str | None = None, **kwargs
        ):
            assert (
                requested_collection_name == collection_name
                or kwargs.get("collection_name") == collection_name
            )

            class _Vectors:
                def keys(self):
                    return {"colorhistogram"}

            class _Params:
                vectors = _Vectors()

            class _Config:
                params = _Params()

            class _Info:
                config = _Config()

            return _Info()

    class _FakeQdrantClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def get_collection(
            self, requested_collection_name: str | None = None, **kwargs
        ):
            return _FakeClient().get_collection(requested_collection_name, **kwargs)

        def upsert(self, *, collection_name: str, points: list[object]) -> None:
            captured["collection_name"] = collection_name
            captured["points"] = points

    captured: dict[str, object] = {}
    monkeypatch.setattr(
        "backend.services.feature_extraction.extract_features_from_bytes",
        lambda _: {"colorhistogram": [0.1, 0.2]},
    )
    monkeypatch.setattr(
        "backend.services.qdrant_client.QdrantClient", _FakeQdrantClient
    )
    monkeypatch.setattr(
        "backend.services.qdrant_client.get_qdrant_settings",
        lambda: get_qdrant_settings().model_copy(
            update={"collection_name": collection_name}
        ),
    )
    monkeypatch.setattr(
        "backend.config.get_qdrant_settings",
        lambda: get_qdrant_settings().model_copy(
            update={"collection_name": collection_name}
        ),
    )

    result = asyncio.run(
        index_segment_to_qdrant(
            session,
            segment,
            image,
            strain_name="CFG_STRAIN",
            species_name="Cfg Species",
            media_name="CFG_MEDIA",
        )
    )

    assert result["status"] == "indexed"
    state = asyncio.run(
        session.scalar(
            select(QdrantIndexState).where(QdrantIndexState.segment_id == segment.id)
        )
    )
    assert state is not None
    assert state.collection_name == collection_name
    assert captured["collection_name"] == collection_name
    point = captured["points"][0]
    assert point.payload["media"] == "CFG_MEDIA"
    assert point.payload["environment"] == "CFG_MEDIA"


def test_index_segment_to_qdrant_reads_s3_crop_via_relative_segment_key(
    session,
    sample_source_png: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def seed() -> tuple[Segment, Image]:
        species = Species(name="S3 Species")
        media = Media(name="S3_MEDIA")
        strain = Strain(name="S3_STRAIN", species=species, source="test")
        session.add_all([species, media, strain])
        await session.flush()

        image = Image(
            strain_id=strain.id,
            species_id=species.id,
            media_id=media.id,
            file_path="S3_STRAIN/S3_MEDIA/image-123/source.jpg",
            prepared_path="S3_STRAIN/S3_MEDIA/image-123/prepared.jpg",
            pipeline_path="S3_STRAIN/S3_MEDIA/image-123/pipeline_kmeans.jpg",
        )
        session.add(image)
        await session.flush()
        segment = Segment(
            image_id=image.id,
            segment_index=0,
            crop_path="/tmp/random/workdir/segments/segment_0.jpg",
            bbox_x=5,
            bbox_y=6,
            bbox_w=7,
            bbox_h=8,
            segmentation_method="kmeans",
        )
        session.add(segment)
        await session.flush()
        return segment, image

    segment, image = asyncio.run(seed())
    storage = _RecordingStorage(
        {"S3_STRAIN/S3_MEDIA/image-123/segments/segment_0.jpg": sample_source_png}
    )

    class _FakeClient:
        def get_collection(self, collection_name: str | None = None, **kwargs):
            class _Vectors:
                def keys(self):
                    return {"colorhistogram"}

            class _Params:
                vectors = _Vectors()

            class _Config:
                params = _Params()

            class _Info:
                config = _Config()

            return _Info()

    class _FakeQdrantClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def get_collection(self, collection_name: str):
            return _FakeClient().get_collection(collection_name)

        def upsert(self, *, collection_name: str, points: list[object]) -> None:
            pass

    monkeypatch.setattr(
        "backend.services.feature_extraction.extract_features_from_bytes",
        lambda data: {"colorhistogram": [float(len(data))]},
    )
    monkeypatch.setattr(
        "backend.services.qdrant_client.QdrantClient", _FakeQdrantClient
    )

    result = asyncio.run(
        index_segment_to_qdrant(
            session,
            segment,
            image,
            strain_name="S3_STRAIN",
            species_name="S3 Species",
            media_name="S3_MEDIA",
            storage=storage,
        )
    )

    assert result["status"] == "indexed"
    assert storage.calls[0].endswith("segments/segment_0.jpg")
    assert "S3_STRAIN/S3_MEDIA/image-123/segments/segment_0.jpg" in storage.calls
