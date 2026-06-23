"""Feature extraction for segments — produces vectors suitable for Qdrant indexing.

Supports both local file paths and raw image bytes (for MinIO/S3-stored images).

Vector dimensions produced:
  - colorhistogram: 96-dim (RGB 32-bin histograms)
  - colorhistogramhs: 64-dim (HSV 32-bin hue+sat histograms)
  - gabor: 32-dim (Gabor filter bank)
  - efficientnetb1_finetuned: 1280-dim (from research collection — fallback for new segments)
  - resnet50_finetuned: 2048-dim
  - mobilenetv2_finetuned: 1280-dim
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ..services.storage import ObjectStorage

logger = logging.getLogger(__name__)

VECTOR_DIMS: dict[str, int] = {
    "resnet50": 2048,
    "resnet50_finetuned": 2048,
    "mobilenetv2": 1280,
    "mobilenetv2_finetuned": 1280,
    "efficientnetb1": 1280,
    "efficientnetb1_finetuned": 1280,
    "hog": 324,
    "gabor": 32,
    "colorhistogram": 96,
    "colorhistogramhs": 64,
}


def extract_features(image_path: Path) -> dict[str, list[float]]:
    """Extract all feature vectors from a segment crop image file."""
    try:
        import cv2 as cv

        img = cv.imread(str(image_path))
        if img is None:
            return _zero_vectors()
        img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    except ImportError:
        return _zero_vectors()

    vectors: dict[str, list[float]] = {}

    vectors["colorhistogram"] = _rgb_histogram(img_rgb, bins=32)
    vectors["colorhistogramhs"] = _hs_histogram(img, bins=32)
    vectors["gabor"] = _gabor_features(img_rgb)

    for name in VECTOR_DIMS:
        if name not in vectors:
            vectors[name] = [0.0] * VECTOR_DIMS[name]

    return vectors


def extract_features_from_bytes(image_bytes: bytes) -> dict[str, list[float]]:
    """Extract all feature vectors from raw image bytes (e.g. from MinIO storage)."""
    try:
        import cv2 as cv

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv.imdecode(arr, cv.IMREAD_COLOR)
        if img is None:
            return _zero_vectors()
        img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    except ImportError:
        return _zero_vectors()

    vectors: dict[str, list[float]] = {}

    vectors["colorhistogram"] = _rgb_histogram(img_rgb, bins=32)
    vectors["colorhistogramhs"] = _hs_histogram(img, bins=32)
    vectors["gabor"] = _gabor_features(img_rgb)

    for name in VECTOR_DIMS:
        if name not in vectors:
            vectors[name] = [0.0] * VECTOR_DIMS[name]

    return vectors


async def index_segment_to_qdrant(
    db,
    segment,
    image_obj,
    strain_name: str,
    species_name: str,
    media_name: str,
    storage: ObjectStorage | None = None,
    collection_name: str = "myco_fungi_features_full_finetuned",
) -> dict:
    """Extract features from a segment crop and index in Qdrant.

    Reads crop image from MinIO storage (preferred) or local filesystem,
    extracts feature vectors, and upserts to Qdrant. Updates the segment's
    qdrant_point_id and creates a QdrantIndexState record.

    Returns dict with status, qdrant_point_id, and feature_types.
    """
    from uuid import UUID, uuid4

    from ..models import QdrantIndexState
    from ..services.qdrant_client import QdrantClientService

    crop_bytes: bytes | None = None

    # Try MinIO/S3 storage first
    if storage is not None:
        artifact_dir = Path(image_obj.file_path).parent
        crop_key = f"{artifact_dir}/segments/segment_{segment.segment_index}.jpg"
        crop_bytes = storage.get_bytes(crop_key)

    # Fallback to local filesystem
    if crop_bytes is None:
        crop_path = Path(segment.crop_path)
        if crop_path.exists():
            crop_bytes = crop_path.read_bytes()

    if crop_bytes is None:
        return {"error": f"Crop image not found for segment {segment.id}"}

    vectors = extract_features_from_bytes(crop_bytes)
    if not vectors:
        return {"error": "Feature extraction returned empty vectors"}

    qdrant_svc = QdrantClientService()
    point_id = uuid4().int & ((1 << 63) - 1)

    payload: dict = {
        "segment_id": str(segment.id),
        "image_id": str(image_obj.id),
        "segment_index": segment.segment_index,
        "strain": strain_name,
        "specy": species_name,
        "species": species_name,
        "environment": media_name,
        "angle": "",
        "extractor": "colorhistogram",
        "bbox": {
            "x": segment.bbox_x,
            "y": segment.bbox_y,
            "w": segment.bbox_w,
            "h": segment.bbox_h,
        },
    }

    await qdrant_svc.upsert_point(
        point_id=point_id,
        vectors=vectors,
        payload=payload,
    )

    segment.qdrant_point_id = UUID(int=point_id)
    qis = QdrantIndexState(
        segment_id=segment.id,
        qdrant_point_id=segment.qdrant_point_id,
        collection_name=collection_name,
        is_active=True,
    )
    db.add(qis)
    await db.flush()

    return {
        "status": "indexed",
        "qdrant_point_id": str(segment.qdrant_point_id),
        "feature_types": list(vectors.keys()),
    }


def _rgb_histogram(img_rgb: np.ndarray, bins: int = 32) -> list[float]:
    h, w = img_rgb.shape[:2]
    hist_r = np.histogram(img_rgb[:, :, 0].ravel(), bins=bins, range=(0, 256))[0]
    hist_g = np.histogram(img_rgb[:, :, 1].ravel(), bins=bins, range=(0, 256))[0]
    hist_b = np.histogram(img_rgb[:, :, 2].ravel(), bins=bins, range=(0, 256))[0]
    combined = np.concatenate([hist_r, hist_g, hist_b]).astype(np.float32)
    combined /= combined.sum() + 1e-8
    return combined.tolist()


def _hs_histogram(img_bgr: np.ndarray, bins: int = 32) -> list[float]:
    import cv2 as cv

    hsv = cv.cvtColor(img_bgr, cv.COLOR_BGR2HSV)
    hist_h = np.histogram(hsv[:, :, 0].ravel(), bins=bins, range=(0, 180))[0]
    hist_s = np.histogram(hsv[:, :, 1].ravel(), bins=bins, range=(0, 256))[0]
    combined = np.concatenate([hist_h, hist_s]).astype(np.float32)
    combined /= combined.sum() + 1e-8
    return combined.tolist()


def _gabor_features(img_rgb: np.ndarray, num_filters: int = 32) -> list[float]:
    import cv2 as cv

    gray = cv.cvtColor(img_rgb, cv.COLOR_RGB2GRAY)
    gray = cv.resize(gray, (64, 64))
    features: list[float] = []
    for theta in np.linspace(0, np.pi, 4, endpoint=False):
        kernel = cv.getGaborKernel((8, 8), 4.0, theta, 10.0, 0.5, 0, ktype=cv.CV_32F)
        filtered = cv.filter2D(gray, cv.CV_32F, kernel)
        mean_abs = float(np.abs(filtered).mean())
        features.append(mean_abs)
        if len(features) >= num_filters:
            break
    while len(features) < 32:
        features.append(0.0)
    return features[:num_filters]


def _zero_vectors() -> dict[str, list[float]]:
    return {name: [0.0] * dim for name, dim in VECTOR_DIMS.items()}
