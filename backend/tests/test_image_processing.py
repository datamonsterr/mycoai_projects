import numpy as np
import pytest

from backend import image_processing


def test_module_importable() -> None:
    assert hasattr(image_processing, "load_image_bytes")


def test_load_image_bytes_color() -> None:
    import cv2

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    data = buf.tobytes()

    result = image_processing.load_image_bytes(data, grayscale=False)
    assert isinstance(result, np.ndarray)
    assert result.ndim == 3
    assert result.shape[2] == 3


def test_load_image_bytes_grayscale() -> None:
    import cv2

    img = np.zeros((10, 10, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".png", img)
    data = buf.tobytes()

    result = image_processing.load_image_bytes(data, grayscale=True)
    assert isinstance(result, np.ndarray)
    assert result.ndim == 2


def test_load_image_bytes_invalid_data() -> None:
    with pytest.raises(ValueError, match="Failed to decode"):
        image_processing.load_image_bytes(b"not an image")


def test_load_image_bytes_empty() -> None:
    import cv2 as cv

    with pytest.raises(cv.error):
        image_processing.load_image_bytes(b"")
