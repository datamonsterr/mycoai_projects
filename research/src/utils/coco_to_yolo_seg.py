from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def _normalize_polygon(coords: list[float], width: int, height: int) -> list[float]:
    norm: list[float] = []
    for idx, value in enumerate(coords):
        scale = width if idx % 2 == 0 else height
        norm.append(value / scale)
    return norm


def convert_coco_split_to_yolo_seg(source_dir: Path, target_dir: Path) -> dict[str, Any]:
    annotations_path = source_dir / "_annotations.coco.json"
    if not annotations_path.exists():
        raise FileNotFoundError(f"Missing COCO annotations: {annotations_path}")

    data = json.loads(annotations_path.read_text())
    images = {image["id"]: image for image in data.get("images", [])}
    grouped: dict[int, list[dict[str, Any]]] = {}
    for ann in data.get("annotations", []):
        grouped.setdefault(ann["image_id"], []).append(ann)

    images_dir = target_dir / "images"
    labels_dir = target_dir / "labels"
    images_dir.mkdir(parents=True, exist_ok=True)
    labels_dir.mkdir(parents=True, exist_ok=True)

    converted = 0
    for image_id, image in images.items():
        source_image = source_dir / image["file_name"]
        if not source_image.exists():
            continue
        shutil.copy2(source_image, images_dir / image["file_name"])

        width = int(image["width"])
        height = int(image["height"])
        label_lines: list[str] = []
        for ann in grouped.get(image_id, []):
            if ann.get("iscrowd"):
                continue
            segmentation = ann.get("segmentation") or []
            polygons = segmentation if segmentation and isinstance(segmentation[0], list) else [segmentation]
            for polygon in polygons:
                if not polygon or len(polygon) < 6:
                    continue
                normalized = _normalize_polygon(polygon, width, height)
                label_lines.append("0 " + " ".join(f"{value:.6f}" for value in normalized))

        (labels_dir / f"{Path(image['file_name']).stem}.txt").write_text(
            "\n".join(label_lines) + ("\n" if label_lines else "")
        )
        converted += 1

    return {
        "source_dir": str(source_dir),
        "target_dir": str(target_dir),
        "converted_images": converted,
    }


def build_yolo_seg_dataset_from_coco_export(source_root: Path, output_root: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {"splits": {}}
    for source_name, target_name in [("train", "train"), ("valid", "val"), ("test", "test")]:
        source_dir = source_root / source_name
        target_dir = output_root / target_name
        summary["splits"][target_name] = convert_coco_split_to_yolo_seg(source_dir, target_dir)

    yaml_text = "\n".join(
        [
            f"path: {output_root.resolve()}",
            "train: train/images",
            "val: val/images",
            "test: test/images",
            "names:",
            "  0: colony",
            "",
        ]
    )
    (output_root / "dataset.yaml").write_text(yaml_text)
    (output_root / "classes.txt").write_text("colony\n")
    return summary
