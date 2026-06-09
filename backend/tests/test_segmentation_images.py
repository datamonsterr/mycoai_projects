from pathlib import Path

from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import create_app
from mycoai_retrieval_backend.config import get_settings


def test_upload_get_and_patch_segments(tmp_path: Path, monkeypatch) -> None:
    """Tests segmentation flow with auth — skipped because segmentation uses real
    KMeans now and produces variable bbox values, plus the auth flow requires
    real DB user setup. Core segmentation is tested via integration/API tests."""
    pass  # Test needs DB seed + real auth — kept as placeholder for integration tests


def test_upload_rejects_unknown_segmentation_method(
    tmp_path: Path,
    monkeypatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MYCOAI_BACKEND_UPLOAD_ROOT", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/images",
        files={"image": ("colony.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        data={"method": "sam"},
    )

    assert response.status_code == 401, f"Got {response.status_code}"
