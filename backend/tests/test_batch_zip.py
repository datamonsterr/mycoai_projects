"""Tests for the batch ZIP upload endpoint (/api/v1/images/batch-zip)."""

import asyncio
import threading
import time
import zipfile
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.image_models import BatchImageStatus
from backend.routes import (
    _BATCH_PROGRESS,
    SEGMENT_CONCURRENCY_LIMIT,
    _batch_progress,
)


def _create_test_zip() -> BytesIO:
    """Create an in-memory ZIP file matching the expected batch structure."""
    import cv2 as cv

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # AGENTS.md
        zf.writestr("AGENTS.md", "# MycoAI Batch Test\n\nTest instructions.")

        # images/ folder with strain subfolders
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        cv_center = (32, 32)
        for y in range(64):
            for x in range(64):
                if (x - cv_center[0]) ** 2 + (y - cv_center[1]) ** 2 <= 20**2:
                    img[y, x] = [200, 180, 160]

        success, encoded = cv.imencode(".jpg", img)
        assert success

        zf.writestr("images/T379/T379_MEA.jpg", encoded.tobytes())
        zf.writestr("images/T379/T379_CYA.jpg", encoded.tobytes())
        zf.writestr("images/T362/T362_MEA.jpg", encoded.tobytes())

    buf.seek(0)
    return buf


@pytest.fixture(name="owner_token")
def fixture_owner_token(client: TestClient) -> str:
    """Login as the seeded owner user and return access token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "owner@mycoai.dev", "password": "password123"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(name="test_zip")
def fixture_test_zip() -> BytesIO:
    return _create_test_zip()


def _get_progress(client: TestClient, owner_token: str, batch_id: str) -> dict:
    resp = client.get(
        f"/api/v1/images/batches/{batch_id}/progress",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 200
    return resp.json()


def _wait_for_batch_completion(
    client: TestClient, owner_token: str, batch_id: str, *, attempts: int = 80
) -> dict:
    del client, owner_token
    time.sleep(0.5)
    for _ in range(attempts):
        progress = _BATCH_PROGRESS[batch_id].model_dump()
        if progress["status"] != "processing":
            return progress
        time.sleep(0.25)
    raise AssertionError(f"batch {batch_id} did not finish")


@pytest.mark.asyncio
class TestBatchZipUpload:
    """Tests for POST /api/v1/images/batch-zip."""

    async def test_requires_authentication(
        self, client: TestClient, test_zip: BytesIO
    ):
        """Anonymous requests should be rejected."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
        )
        assert resp.status_code == 401

    async def test_requires_owner_role(
        self, client: TestClient, test_zip: BytesIO
    ):
        """Non-owner users should be rejected."""
        # Register + login as normal user
        import uuid

        email = f"user-{uuid.uuid4().hex[:6]}@test.com"
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123", "name": "Test User"},
        )
        login_resp = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "password123"},
        )
        user_token = login_resp.json()["access_token"]

        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert resp.status_code in (401, 403), (
            f"Expected 401/403, got {resp.status_code}: {resp.text}"
        )

    async def test_batch_zip_defaults_segmentation_method_to_yolo(
        self,
        client: TestClient,
        owner_token: str,
        test_zip: BytesIO,
        monkeypatch: pytest.MonkeyPatch,
    ):
        captured: dict[str, str] = {}

        class DummyTask:
            def cancel(self) -> bool:
                return True

        original_create_task = asyncio.create_task

        def fake_create_task(coro):
            frame = getattr(coro, "cr_frame", None)
            if frame and "method" in frame.f_locals:
                captured["method"] = frame.f_locals["method"]
                coro.close()
                return DummyTask()
            return original_create_task(coro)

        import backend.routes as routes_module

        monkeypatch.setattr(routes_module.asyncio, "create_task", fake_create_task)

        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            data={"default_media": "MEA", "default_species": "thymicola"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

        assert resp.status_code == 202, f"Request failed: {resp.text}"
        assert captured["method"] == "yolo"

    async def test_owner_can_upload_zip(
        self, client: TestClient, owner_token: str, test_zip: BytesIO
    ):
        """Owner gets batch id immediately; completion comes via progress."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            data={"default_media": "MEA", "default_species": "thymicola"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202, f"Request failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "processing"
        assert data["total"] >= 3
        assert data["successful"] == 0
        assert data["failed"] == 0
        assert data["results"] == []
        assert data["errors"] == []
        assert isinstance(data["batch_name"], str)

        progress = _wait_for_batch_completion(client, owner_token, data["batch_id"])
        assert progress["status"] in {"completed", "completed_with_errors"}
        assert progress["segmentation"]["completed"] >= 1

    async def test_rejects_non_zip_file(self, client: TestClient, owner_token: str):
        """Non-ZIP files should be rejected with 422."""
        txt_file = BytesIO(b"not a zip file")
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.txt", txt_file, "text/plain")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        if resp.status_code == 422:
            assert "Only .zip files" in resp.json()["detail"]
        else:
            # May also get a zipfile error from Python
            assert resp.status_code in (422, 500), resp.text

    async def test_uploaded_images_persisted_in_db(
        self,
        client: TestClient,
        owner_token: str,
        test_zip: BytesIO,
    ):
        """Images from ZIP should be queryable after background completion."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            data={"default_media": "MEA", "default_species": "thymicola"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202
        batch_id = resp.json()["batch_id"]
        _wait_for_batch_completion(client, owner_token, batch_id)

        list_resp = client.get(
            "/api/v1/images",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] >= 1

    async def test_empty_zip_handled_gracefully(
        self, client: TestClient, owner_token: str
    ):
        """ZIP with no images should return 0 successful."""
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("AGENTS.md", "# Empty batch\n")
        buf.seek(0)

        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("empty.zip", buf, "application/zip")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["total"] == 0
        assert data["successful"] == 0

    async def test_result_fields_match_schema(
        self, client: TestClient, owner_token: str, test_zip: BytesIO
    ):
        """Verify each result entry has expected fields."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        for result in data["results"]:
            assert "image_id" in result
            assert "strain" in result
            assert "media" in result
            assert "species" in result
            assert "segments" in result, f"Missing segments in: {result}"
            assert "filename" in result
            assert result["segments"] >= 0

    async def test_batch_zip_returns_progress_contract(
        self, client: TestClient, owner_token: str, test_zip: BytesIO
    ):
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["batch_id"]
        assert data["progress"]["upload"]["total"] == data["total"]
        assert data["progress"]["segmentation"]["total"] == data["total"]
        assert data["progress"]["feature_extraction"]["percent"] >= 0
        assert len(data["progress"]["images"]) == data["total"]

        progress_resp = client.get(
            f"/api/v1/images/batches/{data['batch_id']}/progress",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert progress_resp.status_code == 200
        assert progress_resp.json()["batch_id"] == data["batch_id"]

    async def test_batch_zip_returns_before_segmentation_finishes(
        self,
        client: TestClient,
        owner_token: str,
        test_zip: BytesIO,
        monkeypatch: pytest.MonkeyPatch,
    ):
        import backend.routes as routes_module

        original = routes_module.SegmentationPipeline.segment_upload
        started = threading.Event()
        release = threading.Event()

        def slow_segment_upload(self, *args, **kwargs):
            started.set()
            release.wait(timeout=5)
            return original(self, *args, **kwargs)

        monkeypatch.setattr(
            routes_module.SegmentationPipeline,
            "segment_upload",
            slow_segment_upload,
        )

        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        data = resp.json()
        assert resp.status_code == 202
        assert data["status"] == "processing"
        assert data["successful"] == 0
        assert data["failed"] == 0
        assert data["results"] == []
        assert started.is_set()
        assert any(
            image["status"] == "uploaded" for image in data["progress"]["images"]
        )

        progress_resp = client.get(
            f"/api/v1/images/batches/{data['batch_id']}/progress",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert progress_resp.status_code == 200
        assert progress_resp.json()["status"] == "processing"

        release.set()
        time.sleep(0.05)
        _BATCH_PROGRESS.pop(data["batch_id"], None)

    async def test_confirm_strain_starts_feature_extraction_progress(
        self, client: TestClient, owner_token: str, test_zip: BytesIO
    ):
        upload_resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert upload_resp.status_code == 202
        data = upload_resp.json()
        progress = _wait_for_batch_completion(client, owner_token, data["batch_id"])
        strain = progress["strains"][0]["strain"]
        confirm_resp = client.post(
            f"/api/v1/images/batches/{data['batch_id']}/strains/{strain}/confirm",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert confirm_resp.status_code == 200
        confirmed = next(
            s for s in confirm_resp.json()["strains"] if s["strain"] == strain
        )
        assert confirmed["confirmed"] is True
        assert (
            confirmed["feature_extraction"]["completed"]
            == confirmed["feature_extraction"]["total"]
        )


def test_batch_progress_counts_failures_without_500_state():
    progress = _batch_progress(
        "batch-1",
        "batch",
        [
            BatchImageStatus(
                filename="ok.jpg",
                strain="T1",
                media="MEA",
                species="sp",
                status="segmented",
            ),
            BatchImageStatus(
                filename="bad.jpg",
                strain="T1",
                media="MEA",
                species="sp",
                status="failed",
                error="bad image",
            ),
        ],
    )
    assert progress.status == "completed_with_errors"
    assert progress.upload.completed == 1
    assert progress.segmentation.completed == 1
    assert progress.images[1].error == "bad image"


@pytest.mark.asyncio
async def test_batch_progress_updates_incrementally_during_background_job(
    client: TestClient,
    owner_token: str,
    test_zip: BytesIO,
    monkeypatch: pytest.MonkeyPatch,
):
    import backend.routes as routes_module

    original = routes_module.SegmentationPipeline.segment_upload
    fast_done = threading.Event()
    release_slow = threading.Event()

    def staged_segment_upload(self, image_path, *args, **kwargs):
        if image_path.name == "T379_MEA.jpg":
            fast_done.set()
            return original(self, image_path, *args, **kwargs)
        if image_path.name == "T379_CYA.jpg":
            fast_done.wait(timeout=5)
            release_slow.wait(timeout=5)
        return original(self, image_path, *args, **kwargs)

    class DummyObj:
        def __init__(self, id_value: str):
            self.id = id_value

    async def fake_ensure_species(db, species):
        return DummyObj("species-1")

    async def fake_ensure_media(db, media):
        return DummyObj("media-1")

    async def fake_ensure_strain(db, strain, species_id):
        return DummyObj("strain-1")

    async def fake_create_image(
        db, record, strain_obj, species_obj, media_obj, **kwargs
    ):
        image = DummyObj(f"image-{record.source_path.stem}")
        image.segments = []
        return image

    monkeypatch.setattr(
        routes_module.SegmentationPipeline,
        "segment_upload",
        staged_segment_upload,
    )
    monkeypatch.setattr(routes_module, "_ensure_species", fake_ensure_species)
    monkeypatch.setattr(routes_module, "_ensure_media", fake_ensure_media)
    monkeypatch.setattr(routes_module, "_ensure_strain", fake_ensure_strain)
    monkeypatch.setattr(routes_module, "_create_image", fake_create_image)

    resp = client.post(
        "/api/v1/images/batch-zip",
        files={"zipfile": ("test.zip", test_zip, "application/zip")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert resp.status_code == 202
    batch_id = resp.json()["batch_id"]

    assert fast_done.wait(timeout=5)
    for _ in range(50):
        progress = _get_progress(client, owner_token, batch_id)
        segmented = [img for img in progress["images"] if img["status"] == "segmented"]
        uploaded = [img for img in progress["images"] if img["status"] == "uploaded"]
        if segmented and uploaded:
            break
        time.sleep(0.05)
    else:
        raise AssertionError(
            "expected mixed uploaded/segmented progress before completion"
        )

    assert progress["segmentation"]["completed"] >= 1
    assert progress["segmentation"]["completed"] < progress["segmentation"]["total"]
    release_slow.set()
    _wait_for_batch_completion(client, owner_token, batch_id)
    _BATCH_PROGRESS.pop(batch_id, None)


def test_segmentation_concurrency_limit_is_bounded():
    assert SEGMENT_CONCURRENCY_LIMIT == 2


def test_batch_progress_counts_uploaded_rows_as_uploaded_even_before_segmentation():
    progress = _batch_progress(
        "batch-2",
        "batch",
        [
            BatchImageStatus(
                filename="images/T1/MEA/a.jpg",
                strain="T1",
                media="MEA",
                species="sp",
                status="uploaded",
                image_id="img-1",
                source_url="/api/v1/images/img-1/source",
            )
        ],
    )
    assert progress.upload.completed == 1
    assert progress.segmentation.completed == 0
    assert progress.images[0].image_id == "img-1"


def test_batch_preview_nested_media_folder_keeps_strain_bucketing():
    from pathlib import Path

    from backend.routes import (
        _extract_species_and_strain_from_path,
        _extract_strain_from_path,
        _parse_filename_metadata,
    )

    rel = Path("images/penicillium-thymicola/T379/MEA/T379_plate_01.jpg")
    assert _extract_strain_from_path(rel) == "T379"
    assert _extract_species_and_strain_from_path(rel) == (
        "penicillium-thymicola",
        "T379",
    )
    meta = _parse_filename_metadata(rel.name, str(rel))
    assert meta["media"] == "unknown"


def test_batch_progress_counts_extracting_as_segmented_not_indexed():
    progress = _batch_progress(
        "batch-3",
        "batch",
        [
            BatchImageStatus(
                filename="images/T1/MEA/a.jpg",
                strain="T1",
                media="MEA",
                species="sp",
                status="extracting",
                image_id="img-1",
            )
        ],
    )
    assert progress.upload.completed == 1
    assert progress.segmentation.completed == 1
    assert progress.feature_extraction.completed == 0
    assert progress.status == "processing"
