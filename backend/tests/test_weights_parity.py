from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from backend.segmentation import SegmentationPipeline, _get_yolo_model
from backend.services.feature_extraction import _resolve_finetuned_weights


def test_get_yolo_model_prefers_research_finetuned_weights(tmp_path: Path) -> None:
    finetuned = tmp_path / "weights" / "segmentation" / "yolo_segmentation_best.pt"
    generic = tmp_path / "weights" / "yolo26n-seg.pt"
    finetuned.parent.mkdir(parents=True)
    finetuned.write_bytes(b"finetuned")
    generic.write_bytes(b"generic")

    with patch("backend.segmentation._YOLO_MODEL", None), patch(
        "backend.segmentation._YOLO_WEIGHTS_PATH", None
    ), patch("backend.segmentation.Path.cwd", return_value=tmp_path), patch(
        "backend.segmentation.Path.exists",
        autospec=True,
        side_effect=lambda path: Path(path) in {finetuned, generic},
    ), patch("ultralytics.YOLO", return_value=object()) as yolo:
        model = _get_yolo_model()

    assert model is not None
    yolo.assert_called_once_with(str(finetuned))


def test_resolve_finetuned_weights_prefers_fold0_efficientnet_snapshot(
    tmp_path: Path,
) -> None:
    generic = tmp_path / "weights" / "yolo_finetuned" / "EfficientNetB1_finetuned.pth"
    fold0 = tmp_path / "weights" / "folds" / "fold0_EfficientNetB1_finetuned.pth"
    generic.parent.mkdir(parents=True)
    fold0.parent.mkdir(parents=True)
    generic.write_bytes(b"generic")
    fold0.write_bytes(b"fold0")

    with patch("backend.services.feature_extraction._WEIGHTS_DIR", tmp_path / "weights"):
        weights_path = _resolve_finetuned_weights("EfficientNetB1")

    assert weights_path == fold0


def test_yolo_segmentation_uses_research_parity_imgsz_640() -> None:
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    empty_boxes = SimpleNamespace(xyxy=np.empty((0, 4)), conf=np.empty((0,)))
    model = MagicMock(return_value=[SimpleNamespace(boxes=empty_boxes)])

    with patch("backend.segmentation._get_yolo_model", return_value=model), patch(
        "backend.segmentation.SegmentationPipeline._kmeans_bboxes",
        return_value=[],
    ):
        SegmentationPipeline._yolo_bboxes(image)

    model.assert_called_once_with(
        image,
        verbose=False,
        conf=0.15,
        imgsz=640,
        end2end=False,
    )
