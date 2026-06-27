from pathlib import Path

from src.experiments.feature_extraction.feature_extractors import (
    EfficientNetB1FinetunedExtractor,
    MobileNetV2FinetunedExtractor,
    ResNet50FinetunedExtractor,
)
from src.experiments.feature_extraction.generate_features import (
    _load_prepared_segment_items,
    generate_features,
)


def test_load_prepared_segment_items_respects_segment_method(tmp_path: Path) -> None:
    yolo_path = tmp_path / "species-a" / "dto-100-a1" / "mea" / "ob" / "segments_yolo" / "segment_1.jpg"
    kmeans_path = tmp_path / "species-a" / "dto-100-a1" / "mea" / "ob" / "segments_kmeans" / "segment_1.jpg"
    yolo_path.parent.mkdir(parents=True)
    kmeans_path.parent.mkdir(parents=True)
    yolo_path.write_bytes(b"yolo")
    kmeans_path.write_bytes(b"kmeans")

    yolo_items = _load_prepared_segment_items(tmp_path, segment_method="yolo")
    kmeans_items = _load_prepared_segment_items(tmp_path, segment_method="kmeans")

    assert len(yolo_items) == 1
    assert yolo_items[0]["segmentation"]["method"] == "yolo"
    assert "segments_yolo" in yolo_items[0]["paths"]["segments"][0]

    assert len(kmeans_items) == 1
    assert kmeans_items[0]["segmentation"]["method"] == "kmeans"
    assert "segments_kmeans" in kmeans_items[0]["paths"]["segments"][0]


def test_finetuned_extractors_use_segment_method_weight_exports(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.experiments.feature_extraction.feature_extractors.WEIGHTS_DIR",
        Path("/tmp/weights"),
    )
    monkeypatch.setenv("MYCOAI_FINETUNED_SEGMENT_METHOD", "kmeans")

    resnet = ResNet50FinetunedExtractor.__new__(ResNet50FinetunedExtractor)
    mobilenet = MobileNetV2FinetunedExtractor.__new__(MobileNetV2FinetunedExtractor)
    efficientnet = EfficientNetB1FinetunedExtractor.__new__(EfficientNetB1FinetunedExtractor)

    assert str(resnet._resolve_default_weights_path()) == "/tmp/weights/kmeans_finetuned/ResNet50_finetuned.pth"
    assert str(mobilenet._resolve_default_weights_path()) == "/tmp/weights/kmeans_finetuned/MobileNetV2_finetuned.pth"
    assert str(efficientnet._resolve_default_weights_path()) == "/tmp/weights/kmeans_finetuned/EfficientNetB1_finetuned.pth"


def test_generate_features_ignores_collection_metadata_when_image_dir_provided(tmp_path: Path, monkeypatch) -> None:
    yolo_path = tmp_path / "species-a" / "dto-100-a1" / "mea" / "ob" / "segments_yolo" / "segment_1.jpg"
    yolo_path.parent.mkdir(parents=True)
    yolo_path.write_bytes(b"fake")

    monkeypatch.setattr(
        "src.experiments.feature_extraction.generate_features._load_all_items",
        lambda _: [{"item_id": "metadata-item", "paths": {"segments": ["Dataset/other/segment_1.jpg"]}}],
    )
    used = {"called": False}

    def fake_load_prepared(dataset_root, segment_method):
        used["called"] = True
        return [{"item_id": "prepared-item", "paths": {"segments": [str(yolo_path.relative_to(tmp_path))]}}]

    monkeypatch.setattr(
        "src.experiments.feature_extraction.generate_features._load_prepared_segment_items",
        fake_load_prepared,
    )

    out = tmp_path / "features.json"
    generate_features(output_path=out, image_dir=tmp_path, segment_method="yolo")

    assert used["called"] is True
