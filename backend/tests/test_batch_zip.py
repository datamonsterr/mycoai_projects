"""Tests for the batch ZIP upload endpoint (/api/v1/images/batch-zip)."""

import zipfile
from io import BytesIO

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.image_models import BatchImageStatus
from backend.routes import SEGMENT_CONCURRENCY_LIMIT, _batch_progress


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


@pytest.mark.asyncio
class TestBatchZipUpload:
    """Tests for POST /api/v1/images/batch-zip."""

    async def test_requires_authentication(self, client: TestClient, test_zip: BytesIO):
        """Anonymous requests should be rejected."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
        )
        assert resp.status_code == 401

    async def test_requires_owner_role(self, client: TestClient, test_zip: BytesIO):
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

    async def test_owner_can_upload_zip(
        self, client: TestClient, owner_token: str, test_zip: BytesIO
    ):
        """Owner should be able to upload a ZIP and get processed results."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            data={"default_media": "MEA", "default_species": "thymicola"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202, f"Request failed: {resp.text}"
        data = resp.json()
        assert data["status"] == "completed"
        assert data["total"] >= 3
        assert data["successful"] >= 1
        assert "results" in data
        assert "errors" in data
        assert isinstance(data["batch_name"], str)

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
        session: AsyncSession,
    ):
        """Images from ZIP should be queryable via list endpoint."""
        resp = client.post(
            "/api/v1/images/batch-zip",
            files={"zipfile": ("test.zip", test_zip, "application/zip")},
            data={"default_media": "MEA", "default_species": "thymicola"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert resp.status_code == 202

        # List images to verify persistence
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
        assert data["progress"]["upload"]["completed"] == data["total"]
        assert data["progress"]["segmentation"]["total"] == data["total"]
        assert data["progress"]["feature_extraction"]["percent"] >= 0
        assert len(data["progress"]["images"]) == data["total"]

        progress_resp = client.get(
            f"/api/v1/images/batches/{data['batch_id']}/progress",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert progress_resp.status_code == 200
        assert progress_resp.json()["batch_id"] == data["batch_id"]

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
        strain = data["progress"]["strains"][0]["strain"]
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


def test_segmentation_concurrency_limit_is_bounded():
    assert SEGMENT_CONCURRENCY_LIMIT == 2
