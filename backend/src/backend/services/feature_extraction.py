"""Feature extraction for segments — produces vectors suitable for Qdrant indexing.

Supports both local file paths and raw image bytes (for MinIO/S3-stored images).

Vector dimensions produced:
  - colorhistogram: 96-dim (RGB 32-bin histograms)
  - colorhistogramhs: 64-dim (HSV 32-bin hue+sat histograms)
  - gabor: 32-dim (Gabor filter bank)
   - efficientnetb1_finetuned: 1280-dim (from research collection)
   - (fallback for new segments)
  - resnet50_finetuned: 2048-dim
  - mobilenetv2_finetuned: 1280-dim
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

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

# ---- Deep Learning feature extraction (lazy-loaded) ----

_MONOREPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_WEIGHTS_DIR = (
    Path("/app/weights")
    if Path("/app/weights").exists()
    else _MONOREPO_ROOT / "research" / "weights"
)
_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)
_DL_INPUT_SIZE = 224

_effnet_model: Any = None
_resnet_model: Any = None
_mobilenet_model: Any = None
_torch_available: bool | None = None


def _check_torch() -> bool:
    global _torch_available
    if _torch_available is None:
        try:
            import torch  # noqa: F401
            import torchvision  # type: ignore[import-untyped]  # noqa: F401

            _torch_available = True
        except ImportError:
            _torch_available = False
    return _torch_available


def _preprocess_dl(img_rgb: np.ndarray):
    import torch
    import torch.nn.functional as F

    t = torch.from_numpy(img_rgb).permute(2, 0, 1).float().div_(255.0)
    t = F.interpolate(
        t.unsqueeze(0),
        size=(_DL_INPUT_SIZE, _DL_INPUT_SIZE),
        mode="bilinear",
        align_corners=False,
    ).squeeze(0)
    mean = torch.tensor(_IMAGENET_MEAN, dtype=t.dtype).view(3, 1, 1)
    std = torch.tensor(_IMAGENET_STD, dtype=t.dtype).view(3, 1, 1)
    t = (t - mean) / std
    return t.unsqueeze(0)


def _resolve_finetuned_weights(name: str) -> Path | None:
    """Search for finetuned weights across known locations (yolo/kmeans/folds)."""
    candidates = [
        _WEIGHTS_DIR / "yolo_finetuned" / f"{name}_finetuned.pth",
        _WEIGHTS_DIR / "kmeans_finetuned" / f"{name}_finetuned.pth",
        _WEIGHTS_DIR / f"{name}_finetuned.pth",
        _WEIGHTS_DIR / "folds" / f"fold0_{name}_finetuned.pth",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _load_efficientnetb1_finetuned():
    global _effnet_model
    if _effnet_model is not None:
        return _effnet_model
    if not _check_torch():
        return None
    import torch
    import torch.nn as nn
    from torchvision.models import efficientnet_b1  # type: ignore[import-untyped]

    model = efficientnet_b1(weights=None)
    weights_path = _resolve_finetuned_weights("EfficientNetB1")
    if weights_path is not None:
        try:
            checkpoint = torch.load(weights_path, map_location="cpu")
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get("state_dict", checkpoint)
            else:
                state_dict = checkpoint
            state_dict = {k.removeprefix("module."): v for k, v in state_dict.items()}
            filtered = {
                k: v for k, v in state_dict.items() if not k.startswith("classifier.")
            }
            model.load_state_dict(filtered, strict=False)
            logger.info("Loaded EfficientNetB1_finetuned weights from %s", weights_path)
        except Exception as exc:
            logger.warning("Failed to load EfficientNetB1_finetuned weights: %s", exc)
            return None
    else:
        logger.warning("No EfficientNetB1_finetuned weights found in %s", _WEIGHTS_DIR)
        return None
    model.classifier = nn.Identity()
    model.eval()
    _effnet_model = model
    return model


def _load_resnet50_finetuned():
    global _resnet_model
    if _resnet_model is not None:
        return _resnet_model
    if not _check_torch():
        return None
    import torch
    import torch.nn as nn
    from torchvision.models import resnet50

    model = resnet50(weights=None)
    weights_path = _resolve_finetuned_weights("ResNet50")
    if weights_path is not None:
        try:
            checkpoint = torch.load(weights_path, map_location="cpu")
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get("state_dict", checkpoint)
            else:
                state_dict = checkpoint
            state_dict = {k.removeprefix("module."): v for k, v in state_dict.items()}
            filtered = {k: v for k, v in state_dict.items() if not k.startswith("fc.")}
            model.load_state_dict(filtered, strict=False)
            logger.info("Loaded ResNet50_finetuned weights from %s", weights_path)
        except Exception as exc:
            logger.warning("Failed to load ResNet50_finetuned weights: %s", exc)
            return None
    else:
        logger.warning("No ResNet50_finetuned weights found in %s", _WEIGHTS_DIR)
        return None
    model.fc = nn.Identity()
    model.eval()
    _resnet_model = model
    return model


def _load_mobilenetv2_finetuned():
    global _mobilenet_model
    if _mobilenet_model is not None:
        return _mobilenet_model
    if not _check_torch():
        return None
    import torch
    import torch.nn as nn
    from torchvision.models import mobilenet_v2

    model = mobilenet_v2(weights=None)
    weights_path = _resolve_finetuned_weights("MobileNetV2")
    if weights_path is not None:
        try:
            checkpoint = torch.load(weights_path, map_location="cpu")
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get("state_dict", checkpoint)
            else:
                state_dict = checkpoint
            state_dict = {k.removeprefix("module."): v for k, v in state_dict.items()}
            filtered = {
                k: v for k, v in state_dict.items() if not k.startswith("classifier.")
            }
            model.load_state_dict(filtered, strict=False)
            logger.info("Loaded MobileNetV2_finetuned weights from %s", weights_path)
        except Exception as exc:
            logger.warning("Failed to load MobileNetV2_finetuned weights: %s", exc)
            return None
    else:
        logger.warning("No MobileNetV2_finetuned weights found in %s", _WEIGHTS_DIR)
        return None
    model.classifier = nn.Identity()
    model.eval()
    _mobilenet_model = model
    return model


def _extract_dl_feature(model, img_rgb: np.ndarray) -> list[float]:
    import torch

    input_tensor = _preprocess_dl(img_rgb)
    with torch.no_grad():
        output = model(input_tensor)
    return output.cpu().flatten().tolist()


def _extract_dl_vectors(vectors: dict[str, list[float]], img_rgb: np.ndarray) -> None:
    if not _check_torch():
        return
    for model_name, loader in [
        ("efficientnetb1_finetuned", _load_efficientnetb1_finetuned),
        ("resnet50_finetuned", _load_resnet50_finetuned),
        ("mobilenetv2_finetuned", _load_mobilenetv2_finetuned),
    ]:
        try:
            model = loader()
            if model is not None:
                vectors[model_name] = _extract_dl_feature(model, img_rgb)
        except Exception as exc:
            logger.warning("DL extraction failed for %s: %s", model_name, exc)


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

    _extract_dl_vectors(vectors, img_rgb)

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

    _extract_dl_vectors(vectors, img_rgb)

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

    vectors = await asyncio.to_thread(extract_features_from_bytes, crop_bytes)
    if not vectors:
        return {"error": "Feature extraction returned empty vectors"}

    qdrant_svc = QdrantClientService()
    # Filter to vectors supported by the collection schema
    try:
        collection_info = await asyncio.to_thread(
            qdrant_svc._client.get_collection, collection_name=collection_name
        )
        collection_vectors = collection_info.config.params.vectors
        supported = (
            set(collection_vectors.keys())
            if isinstance(collection_vectors, dict)
            else set()
        )
        vectors = {k: v for k, v in vectors.items() if k in supported}
        if not vectors:
            return {
                "error": (
                    f"None of the extracted vectors are supported by collection "
                    f"'{collection_name}'. Supported: {sorted(supported)}"
                )
            }
    except Exception as exc:
        logger.warning(
            "Could not resolve supported vectors for %s: %s; using all extracted",
            collection_name,
            exc,
        )

    point_id = uuid4().int & ((1 << 63) - 1)

    payload: dict = {
        "segment_id": str(segment.id),
        "image_id": str(image_obj.id),
        "segment_index": segment.segment_index,
        "strain": strain_name,
        "specy": species_name,
        "species": species_name,
        "media": media_name,
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
