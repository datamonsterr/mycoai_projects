from pathlib import Path

from fastapi.testclient import TestClient

from mycoai_retrieval_backend.app import create_app
from mycoai_retrieval_backend.config import get_settings


def test_upload_get_and_patch_segments(tmp_path: Path, monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MYCOAI_BACKEND_UPLOAD_ROOT", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    upload = client.post(
        "/api/v1/images",
        files={"image": ("colony.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        data={"strain": "agaricus", "media": "pda", "method": "kmeans"},
    )

    assert upload.status_code == 201
    payload = upload.json()
    assert payload["segmentation_method"] == "kmeans"
    assert payload["source_url"].endswith("/source.jpg")
    assert len(payload["segments"]) == 3
    assert payload["segments"][0]["bbox"] == {"x": 63, "y": 52, "w": 72, "h": 72}

    image_id = payload["image_id"]
    fetched = client.get(f"/api/v1/images/{image_id}")

    assert fetched.status_code == 200
    assert fetched.json() == payload

    patched = client.patch(
        f"/api/v1/images/{image_id}/segments",
        json={
            "segments": [
                {"segment_index": 0, "bbox": {"x": 50, "y": 55, "w": 85, "h": 90}}
            ],
            "deleted_segments": [2],
        },
    )

    assert patched.status_code == 200
    updated = patched.json()
    assert [segment["segment_index"] for segment in updated["segments"]] == [0, 1]
    assert updated["segments"][0]["bbox"] == {"x": 50, "y": 55, "w": 85, "h": 90}

    crop = client.get(f"/api/v1/images/{image_id}/segments/0/crop")

    assert crop.status_code == 200
    assert crop.content == b"fake-jpeg-bytes"

    get_settings.cache_clear()


def test_upload_rejects_unknown_segmentation_method(
    tmp_path: Path, monkeypatch
) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("MYCOAI_BACKEND_UPLOAD_ROOT", str(tmp_path / "uploads"))
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/images",
        files={"image": ("colony.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        data={"method": "sam"},
    )

    assert response.status_code == 422
    assert "unsupported segmentation method" in response.json()["detail"]

    get_settings.cache_clear()
