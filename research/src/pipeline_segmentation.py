"""
Pipeline: run kmeans + YOLO segmentation on images from YOLO dataset.
Each leaf folder: source.jpg, prepared.jpg, bbox_kmeans.jpg, pipeline_kmeans.jpg, bbox_yolo.jpg
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import cv2
import numpy as np

from src.config import WEIGHTS_DIR, WORKSPACE_ROOT
from src.preprocessing.kmeans import draw_bbox, segment_kmeans_image
from src.preprocessing.preprocess import process_image


FILE_EXTENSION = ".jpg"
TARGET_SIZE = 256


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    return normalized.strip("-") or "unknown"


def parse_image_name(filename: str) -> dict[str, str]:
    stem = Path(filename).stem
    parts = stem.split("_")
    strain = "unknown"
    environment = "unknown"
    angle = "unknown"
    for i, part in enumerate(parts):
        if part.startswith("DTO") and i + 1 < len(parts):
            strain = f"{part}_{parts[i + 1]}"
            break
        elif part.startswith("DTO"):
            strain = part
            break
    for env in ["CREA", "MEA", "CYA", "CYA30", "CYAS", "YES", "DG18"]:
        if env in parts:
            environment = env
            break
    for ang in ["ob", "rev"]:
        if ang in parts:
            angle = ang
            break
    return {"strain": strain, "environment": environment, "angle": angle}


def _compute_iou(box1: dict, box2: dict) -> float:
    x1 = max(box1["xmin"], box2["xmin"])
    y1 = max(box1["ymin"], box2["ymin"])
    x2 = min(box1["xmax"], box2["xmax"])
    y2 = min(box1["ymax"], box2["ymax"])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    area1 = (box1["xmax"] - box1["xmin"]) * (box1["ymax"] - box1["ymin"])
    area2 = (box2["xmax"] - box2["xmin"]) * (box2["ymax"] - box2["ymin"])
    return inter / (area1 + area2 - inter)


def _filter_non_overlapping(
    bboxes: list[dict], iou_thresh: float = 0.25, max_boxes: int = 3
) -> list[dict]:
    if not bboxes:
        return []
    kept: list[dict] = []
    for box in bboxes:
        if all(_compute_iou(box, kept_box) < iou_thresh for kept_box in kept):
            kept.append(box)
        if len(kept) >= max_boxes:
            break
    return kept


def run_pipeline(
    image_source: Path,
    output_root: Path,
    limit: int | None = None,
) -> dict:
    image_files = (
        sorted(image_source.rglob("*.jpg"))[:limit]
        if limit
        else sorted(image_source.rglob("*.jpg"))
    )
    print(f"Found {len(image_files)} images")

    output_root.mkdir(parents=True, exist_ok=True)
    results = {
        "total": len(image_files),
        "kmeans_ok": 0,
        "yolo_ok": 0,
        "failed": 0,
        "items": [],
    }

    from ultralytics import YOLO

    yolo_weights = WEIGHTS_DIR / "segmentation" / "yolo26_seg_best.pt"
    if not yolo_weights.exists():
        print(f"ERROR: YOLO weights not found at {yolo_weights}")
        sys.exit(1)
    model = YOLO(str(yolo_weights))
    print(f"Loaded YOLO model from {yolo_weights}")

    for idx, img_path in enumerate(image_files):
        try:
            image = cv2.imread(str(img_path))
            if image is None:
                results["failed"] += 1
                continue

            meta = parse_image_name(img_path.name)
            leaf_dir = (
                output_root
                / slugify(meta["strain"])
                / slugify(meta["environment"])
                / meta["angle"]
                / slugify(img_path.stem)[:40]
            )
            leaf_dir.mkdir(parents=True, exist_ok=True)

            source_path = leaf_dir / f"source{FILE_EXTENSION}"
            prepared_path = leaf_dir / f"prepared{FILE_EXTENSION}"
            if not source_path.exists():
                shutil.copy2(img_path, source_path)

            prepared_image = process_image(image, output_size=TARGET_SIZE)
            cv2.imwrite(str(prepared_path), prepared_image)

            # KMeans segmentation
            bboxes_kmeans, _ = segment_kmeans_image(prepared_image)
            if bboxes_kmeans:
                bbox_kmeans_path = leaf_dir / f"bbox_kmeans{FILE_EXTENSION}"
                bbox_kmeans_img = draw_bbox(prepared_image, bboxes_kmeans)
                cv2.imwrite(str(bbox_kmeans_path), bbox_kmeans_img)

                src = cv2.imread(str(source_path))
                if src is not None:
                    pipeline_path = leaf_dir / f"pipeline_kmeans{FILE_EXTENSION}"
                    h, w = prepared_image.shape[:2]
                    src_resized = cv2.resize(src, (w, h), interpolation=cv2.INTER_AREA)
                    pipeline_img = np.hstack(
                        [src_resized, prepared_image, bbox_kmeans_img]
                    )
                    cv2.imwrite(str(pipeline_path), pipeline_img)
                results["kmeans_ok"] += 1

            # YOLO segmentation
            yolo_results = model(
                prepared_image, verbose=False, conf=0.15, imgsz=256, end2end=False
            )
            bboxes_yolo = []
            if yolo_results and yolo_results[0].boxes is not None:
                boxes = yolo_results[0].boxes.xyxy
                confs = yolo_results[0].boxes.conf
                if boxes is not None and len(boxes) > 0 and confs is not None:
                    scored = []
                    for conf_val, box_coords in zip(confs.tolist(), boxes.tolist()):
                        x1, y1, x2, y2 = map(int, box_coords)
                        scored.append(
                            (conf_val, {"xmin": x1, "ymin": y1, "xmax": x2, "ymax": y2})
                        )
                    scored.sort(key=lambda x: -x[0])
                    all_bboxes = [b for _, b in scored]
                    bboxes_yolo = _filter_non_overlapping(
                        all_bboxes, iou_thresh=0.25, max_boxes=3
                    )

            if bboxes_yolo:
                bbox_yolo_path = leaf_dir / f"bbox_yolo{FILE_EXTENSION}"
                bbox_yolo_img = draw_bbox(prepared_image, bboxes_yolo)
                cv2.imwrite(str(bbox_yolo_path), bbox_yolo_img)
                results["yolo_ok"] += 1

            results["items"].append(
                {
                    "leaf_dir": str(leaf_dir.relative_to(output_root)),
                    "kmeans_bboxes": len(bboxes_kmeans) if bboxes_kmeans else 0,
                    "yolo_bboxes": len(bboxes_yolo) if "bboxes_yolo" in dir() else 0,
                }
            )

            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{len(image_files)}")

        except Exception as exc:
            print(f"  ERROR {img_path.name}: {exc}")
            results["failed"] += 1

    metrics_path = output_root / "pipeline_metrics.json"
    metrics_path.write_text(json.dumps(results, indent=2))
    print(
        f"\nPipeline complete: {results['kmeans_ok']} kmeans, {results['yolo_ok']} yolo, {results['failed']} failed"
    )
    print(f"Metrics: {metrics_path}")
    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--image-source", default="/tmp/opencode/yolo_data/train")
    parser.add_argument("--output-root", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    image_source = Path(args.image_source)
    output_root = (
        Path(args.output_root)
        if args.output_root
        else WORKSPACE_ROOT / "Dataset" / "segmented_output"
    )

    run_pipeline(image_source, output_root, limit=args.limit)
