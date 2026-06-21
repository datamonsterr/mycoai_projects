"""Feature extraction for segments — produces vectors suitable for Qdrant indexing.

MVP: color histogram (RGB 96-dim) + HOG (if OpenCV available) or zeros.
Full implementation should add ResNet50/EfficientNetB1 via subprocess.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Named vector dimensions (from technical spec 06-qdrant-integration.md)
VECTOR_DIMS: dict[str, int] = {
    "resnet50": 2048,
    "mobilenetv2": 1280,
    "efficientnetb1": 1280,
    "hog": 324,  # 36 bins * 9 orientations typical
    "gabor": 32,
    "colorhistogram": 96,
    "colorhistogramhs": 64,
    "ResNet50_finetuned": 2048,
    "MobileNetV2_finetuned": 1280,
    "EfficientNetB1_finetuned": 1280,
    "ViT_finetuned": 768,
}


def extract_features(image_path: Path) -> dict[str, list[float]]:
    """Extract all feature vectors from a segment crop image.

    Returns dict of feature_name → vector (list of floats).
    For MVP, produces colorhistogram + colorhistogramhs + gabor.
    Later: add deep learning features via subprocess.
    """
    try:
        import cv2 as cv

        img = cv.imread(str(image_path))
        if img is None:
            return _zero_vectors()
        img_rgb = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    except ImportError:
        return _zero_vectors()

    vectors: dict[str, list[float]] = {}

    # Color histogram (RGB, 96-dim)
    vectors["colorhistogram"] = _rgb_histogram(img_rgb, bins=32)

    # Color histogram HS (from HSV, 64-dim)
    vectors["colorhistogramhs"] = _hs_histogram(img, bins=32)

    # Gabor filter bank (32-dim)
    vectors["gabor"] = _gabor_features(img_rgb)

    # Fill remaining with zeros
    for name in VECTOR_DIMS:
        if name not in vectors:
            vectors[name] = [0.0] * VECTOR_DIMS[name]

    return vectors


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
