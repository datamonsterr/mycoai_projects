import json
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from tqdm import tqdm

from src.config import (
    FEATURES_JSON_PATH,
    COLLECTION_METADATA_PATHS,
    ORIGINAL_PREPARED_DATASET_DIR,
    WORKSPACE_ROOT,
)
from src.experiments.feature_extraction.feature_extractors import (
    ColorHistogramExtractor,
    ColorHistogramHSconcatResnet50,
    ColorHistogramHSExtractor,
    EfficientNetB1Extractor,
    EfficientNetB1FinetunedExtractor,
    GaborExtractor,
    HOGExtractor,
    MobileNetV2Extractor,
    MobileNetV2FinetunedExtractor,
    ResNet50Extractor,
    ResNet50FinetunedExtractor,
)


def _load_all_items(metadata_paths: dict[str, Path]) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for path in metadata_paths.values():
        if not path.exists():
            continue
        with open(path, "r") as f:
            items = json.load(f)
            for item in items:
                item["_metadata_source"] = str(path)
            all_items.extend(items)
    return all_items


def _item_from_prepared_segment(segment_path: Path, dataset_root: Path) -> dict[str, Any] | None:
    try:
        relative = segment_path.relative_to(WORKSPACE_ROOT)
        parts = segment_path.relative_to(dataset_root).parts
    except ValueError:
        return None
    if len(parts) < 6:
        return None
    species_slug, strain_slug, environment, angle, segment_dir, filename = parts[:6]
    if segment_dir not in {"segments_yolo", "segments_kmeans"}:
        return None
    item_id = "__".join(parts[:4] + (filename.removesuffix(".jpg"),))
    species = species_slug.replace("-", " ")
    strain_parts = strain_slug.split("-")
    strain = (
        f"{strain_parts[0].upper()} {strain_parts[1]}-{strain_parts[2].upper()}"
        if len(strain_parts) == 3
        else strain_slug.replace("-", " ").upper()
    )
    return {
        "item_id": item_id,
        "paths": {"segments": [str(relative)]},
        "instance_info": {
            "species": species,
            "strain": strain,
            "environment": environment.upper(),
            "angle": angle,
        },
        "segmentation": {"method": segment_dir.removeprefix("segments_")},
        "_segment_filename": filename,
    }


def _load_prepared_segment_items(
    dataset_root: Path = ORIGINAL_PREPARED_DATASET_DIR,
    segment_method: str = "yolo",
) -> list[dict[str, Any]]:
    segment_dir = f"segments_{segment_method}"
    items: list[dict[str, Any]] = []
    if not dataset_root.exists():
        return items
    for segment_path in sorted(dataset_root.glob(f"*/*/*/*/{segment_dir}/segment_*.jpg")):
        item = _item_from_prepared_segment(segment_path, dataset_root)
        if item is not None:
            items.append(item)
    return items


def generate_features(
    metadata_path: Path | None = None,
    output_path: Path = FEATURES_JSON_PATH,
    image_dir: Path | None = None,
) -> None:
    if metadata_path is not None:
        if not metadata_path.exists():
            print(f"Error: Metadata file {metadata_path} not found.")
            return
        with open(metadata_path, "r") as f:
            items = json.load(f)
    else:
        items = _load_all_items(COLLECTION_METADATA_PATHS)
        if not items:
            prepared_root = image_dir or ORIGINAL_PREPARED_DATASET_DIR
            items = _load_prepared_segment_items(prepared_root, segment_method="yolo")

    if not items:
        print("No segment items found in metadata or original_prepared.")
        return

    extractors = [
        ColorHistogramHSconcatResnet50(),
        ResNet50Extractor(),
        ResNet50FinetunedExtractor(),
        MobileNetV2Extractor(),
        MobileNetV2FinetunedExtractor(),
        EfficientNetB1Extractor(),
        EfficientNetB1FinetunedExtractor(),
        HOGExtractor(),
        GaborExtractor(),
        ColorHistogramExtractor(),
        ColorHistogramHSExtractor(),
    ]

    features_data: list[dict[str, Any]] = []
    segment_count = 0

    for item in tqdm(items, desc="Items"):
        item_id = item.get("item_id", "")
        segment_paths = item.get("paths", {}).get("segments", [])
        if not segment_paths:
            continue

        for idx, seg_path in enumerate(segment_paths):
            image_path = WORKSPACE_ROOT / seg_path
            if not image_path.exists():
                continue

            img_cv2 = cv2.imread(str(image_path))
            if img_cv2 is None:
                continue

            segment_id = f"{item_id}_seg{idx}"
            record: dict[str, Any] = {
                "id": segment_id,
                "segment_path": seg_path,
                "metadata": {
                    "instance_info": item.get("instance_info", {}),
                    "segmentation": item.get("segmentation", {}),
                    "index": idx,
                },
                "features": {},
            }

            for extractor in extractors:
                try:
                    if hasattr(extractor, "extract"):
                        vector = extractor.extract(img_cv2)

                        if isinstance(vector, np.ndarray):
                            vector = vector.tolist()
                        elif isinstance(vector, torch.Tensor):
                            vector = vector.cpu().numpy().tolist()

                        record["features"][extractor.name.lower()] = {
                            "vector": vector,
                            "dimension": len(vector),
                        }
                except Exception as e:
                    print(f"Error extracting {extractor.name} for {segment_id}: {e}")

            features_data.append(record)
            segment_count += 1

    with open(output_path, "w") as f:
        json.dump(features_data, f)

    print(f"Extracted features for {segment_count} segments from {len(items)} items")
    print(f"Features saved to {output_path}")


if __name__ == "__main__":
    generate_features()
