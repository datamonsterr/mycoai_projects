import json
from pathlib import Path

from src.utils.coco_to_yolo_seg import build_yolo_seg_dataset_from_coco_export


def test_build_yolo_seg_dataset_from_coco_export(tmp_path: Path) -> None:
    source_root = tmp_path / "coco"
    train_dir = source_root / "train"
    valid_dir = source_root / "valid"
    test_dir = source_root / "test"
    for split_dir in [train_dir, valid_dir, test_dir]:
        split_dir.mkdir(parents=True)
        image_path = split_dir / f"{split_dir.name}_sample.jpg"
        image_path.write_bytes(b"img")
        annotations = {
            "images": [
                {
                    "id": 1,
                    "file_name": image_path.name,
                    "width": 100,
                    "height": 200,
                }
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [10, 20, 50, 60],
                    "iscrowd": 0,
                    "area": 3000,
                    "segmentation": [[10, 20, 60, 20, 60, 80, 10, 80]],
                }
            ],
        }
        (split_dir / "_annotations.coco.json").write_text(json.dumps(annotations))

    output_root = tmp_path / "yolo_seg"
    summary = build_yolo_seg_dataset_from_coco_export(source_root, output_root)

    assert (output_root / "dataset.yaml").exists()
    assert (output_root / "train" / "labels" / "train_sample.txt").exists()
    label_text = (output_root / "train" / "labels" / "train_sample.txt").read_text().strip()
    assert label_text.startswith("0 ")
    assert summary["splits"]["train"]["converted_images"] == 1
