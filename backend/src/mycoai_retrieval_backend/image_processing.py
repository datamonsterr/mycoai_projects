from __future__ import annotations

import cv2
import numpy as np


def load_image_bytes(data: bytes, grayscale: bool = False) -> np.ndarray:
    flags = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, flags)
    if img is None:
        raise ValueError("Failed to decode image from bytes")
    return img
