from __future__ import annotations

import asyncio
import shutil
from collections.abc import Generator
from pathlib import Path
from tempfile import mkdtemp

import cv2 as cv
import numpy as np
import pytest

from backend.segmentation import SegmentationPipeline

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def reset_yolo_singletons():
    import backend.segmentation as segmentation

    segmentation._YOLO_MODEL = None
    segmentation._YOLO_WEIGHTS_PATH = None


@pytest.fixture
def yolo_fixture_dir() -> Generator[Path]:
    work_dir = Path(mkdtemp(prefix="itest_yolo_seg_"))
    image = np.zeros((640, 640, 3), dtype=np.uint8)
    cv.circle(image, (200, 200), 80, (180, 160, 140), -1)
    cv.circle(image, (430, 430), 70, (210, 200, 175), -1)
    cv.imwrite(str(work_dir / "dto_148_c8.jpg"), image)
    yield work_dir
    shutil.rmtree(work_dir, ignore_errors=True)


def test_yolo_segmentation_pipeline_uses_root_finetuned_weights(
    yolo_fixture_dir: Path,
) -> None:
    repo_root = Path("/home/dat/dev/mycoai")
    weights_path = repo_root / "weights" / "segmentation" / "yolo26_seg_best.pt"
    if not weights_path.exists():
        pytest.skip(f"Finetuned YOLO weights not found: {weights_path}")

    pipeline = SegmentationPipeline(upload_root=yolo_fixture_dir)
    from unittest.mock import patch

    with patch("backend.segmentation.Path.cwd", return_value=repo_root):
        record = asyncio.run(
            asyncio.to_thread(
                pipeline.segment_upload,
                yolo_fixture_dir / "dto_148_c8.jpg",
                strain="DTO 148-C8",
                media="CYA",
                method="yolo",
            )
        )

    assert record.segmentation_method == "yolo"
    assert record.source_path.exists()
    assert record.artifact_dir.exists()
    assert len(record.segments) >= 0
