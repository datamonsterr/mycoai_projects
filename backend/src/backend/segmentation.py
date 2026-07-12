from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import TYPE_CHECKING
from uuid import uuid4

import cv2 as cv
import numpy as np
from sklearn.cluster import KMeans  # type: ignore[import-untyped]

from .image_models import BoundingBox, ImageRecord, Segment, SegmentPatchRequest

if TYPE_CHECKING:
    from .services.storage import ObjectStorage

ALLOWED_METHODS = {"kmeans", "contour", "yolo"}

_YOLO_MODEL = None
_YOLO_WEIGHTS_PATH: Path | None = None


def _get_yolo_model(weights: str | Path | None = None) -> object | None:
    global _YOLO_MODEL, _YOLO_WEIGHTS_PATH
    wpath = Path(weights) if weights else None
    if _YOLO_MODEL is not None and wpath == _YOLO_WEIGHTS_PATH:
        return _YOLO_MODEL
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    if wpath is None:
        candidates = [
            Path("/app/segmentation_weights/yolo_segmentation_best.pt"),
            Path("/app/segmentation_weights/yolo26_seg_best.pt"),
            Path("/app/segmentation_weights/yolo26n-seg.pt"),
            Path("/app/segmentation_weights/yolov8n-seg.pt"),
            Path.cwd() / "weights" / "segmentation" / "yolo_segmentation_best.pt",
            Path.cwd() / "weights" / "segmentation" / "yolo26_seg_best.pt",
            Path.cwd() / "weights" / "yolo26n-seg.pt",
            Path.cwd() / "weights" / "yolov8n-seg.pt",
            Path("weights/segmentation/yolo_segmentation_best.pt"),
            Path("weights/segmentation/yolo26_seg_best.pt"),
            Path("weights/yolo26n-seg.pt"),
            Path("weights/yolov8n-seg.pt"),
        ]
        for c in candidates:
            if c.exists():
                wpath = c
                break
        if wpath is not None:
            wpath = Path(wpath)
    if wpath is None or not wpath.exists():
        return None
    _YOLO_MODEL = YOLO(str(wpath))
    _YOLO_WEIGHTS_PATH = wpath
    return _YOLO_MODEL


class ImageStore:
    def __init__(self, upload_root: Path) -> None:
        self.upload_root = upload_root
        self._records: dict[str, ImageRecord] = {}

    def add(self, record: ImageRecord) -> None:
        self._records[record.image_id] = record

    def get(self, image_id: str) -> ImageRecord | None:
        return self._records.get(image_id)


class SegmentationPipeline:
    def __init__(
        self,
        upload_root: Path,
        storage: ObjectStorage | None = None,
    ) -> None:
        self.upload_root = upload_root
        self._storage = storage

    @property
    def _use_storage(self) -> bool:
        return self._storage is not None

    def _storage_key(self, *parts: str) -> str:
        return "/".join(parts)

    def _upload_artifact(self, key: str, path: Path) -> str:
        data = path.read_bytes()
        if self._storage:
            return self._storage.upload_bytes(key, data)
        return f"/static/{key}"

    # ------------------------------------------------------------------
    # Upload + segment
    # ------------------------------------------------------------------
    def segment_upload(
        self,
        source_path: Path,
        *,
        strain: str,
        media: str,
        method: str = "kmeans",
        image_id: str | None = None,
    ) -> ImageRecord:
        if method not in ALLOWED_METHODS:
            raise ValueError(f"unsupported segmentation method: {method}")

        image_id = image_id or uuid4().hex
        prefix = f"{strain}/{media}/{image_id}"
        work_dir = Path(mkdtemp(prefix="seg_"))

        try:
            artifact_dir = (
                self.upload_root / strain / media / image_id
                if not self._use_storage
                else work_dir
            )
            segments_dir = artifact_dir / "segments"
            segments_dir.mkdir(parents=True, exist_ok=True)

            stored_source = artifact_dir / "source.jpg"
            shutil.copyfile(source_path, stored_source)
            prepared_path = artifact_dir / "prepared.jpg"
            shutil.copyfile(stored_source, prepared_path)
            bbox_path = artifact_dir / f"bbox_{method}.jpg"
            pipeline_path = artifact_dir / f"pipeline_{method}.jpg"

            img = cv.imread(str(stored_source))
            if img is None:
                bboxes: list[BoundingBox] = []
            elif method == "kmeans":
                bboxes = self._kmeans_bboxes(img, bbox_path)
            elif method == "yolo":
                bboxes = self._yolo_bboxes(img, bbox_path)
            else:
                bboxes = self._contour_bboxes(img, bbox_path)

            segments = [
                self._write_segment(
                    image_id=image_id,
                    segment_index=index,
                    bbox=bbox,
                    source_path=stored_source,
                    segments_dir=segments_dir,
                    method=method,
                )
                for index, bbox in enumerate(bboxes)
            ]

            if segments:
                self._compose_pipeline(
                    stored_source, prepared_path, bbox_path, pipeline_path
                )
            else:
                shutil.copyfile(stored_source, pipeline_path)

            if self._use_storage:
                assert self._storage is not None
                self._storage.upload_bytes(
                    self._storage_key(prefix, "source.jpg"),
                    stored_source.read_bytes(),
                )
                self._storage.upload_bytes(
                    self._storage_key(prefix, "prepared.jpg"),
                    prepared_path.read_bytes(),
                )
                if bbox_path.exists():
                    self._storage.upload_bytes(
                        self._storage_key(prefix, f"bbox_{method}.jpg"),
                        bbox_path.read_bytes(),
                    )
                self._storage.upload_bytes(
                    self._storage_key(prefix, f"pipeline_{method}.jpg"),
                    pipeline_path.read_bytes(),
                )
                for seg in segments:
                    crop_path = segments_dir / f"segment_{seg.segment_index}.jpg"
                    if crop_path.exists():
                        self._storage.upload_bytes(
                            self._storage_key(
                                prefix, "segments", f"segment_{seg.segment_index}.jpg"
                            ),
                            crop_path.read_bytes(),
                        )

            source_path = (
                Path(prefix) / "source.jpg" if self._use_storage else stored_source
            )
            artifact_root = Path(prefix) if self._use_storage else artifact_dir
            return ImageRecord(
                image_id=image_id,
                source_path=source_path,
                artifact_dir=artifact_root,
                source_url=f"/api/v1/images/{image_id}/source",
                segments=segments,
                segmentation_method=method,
            )
        finally:
            if self._use_storage:
                shutil.rmtree(work_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Update segments (PATCH)
    # ------------------------------------------------------------------
    def update_segments(
        self,
        record: ImageRecord,
        patch: SegmentPatchRequest,
    ) -> ImageRecord:
        deleted = set(patch.deleted_segments)
        by_index = {segment.segment_index: segment for segment in record.segments}

        source_path_local: Path | None = None
        if not self._use_storage:
            source_path_local = record.source_path
        elif self._storage:
            src_key = self._storage_key(str(record.artifact_dir), "source.jpg")
            tmp = Path(mkdtemp(prefix="seg_")) / "source.jpg"
            data = self._read_from_storage(src_key)
            if data is not None:
                tmp.parent.mkdir(parents=True, exist_ok=True)
                tmp.write_bytes(data)
                source_path_local = tmp

        segments_dir = (
            self.upload_root / record.artifact_dir / "segments"
            if not self._use_storage
            else Path(mkdtemp(prefix="seg_")) / "segments"
        )
        segments_dir.mkdir(parents=True, exist_ok=True)

        try:
            for segment_patch in patch.segments:
                if segment_patch.segment_index in deleted:
                    continue
                by_index[segment_patch.segment_index] = self._write_segment(
                    image_id=record.image_id,
                    segment_index=segment_patch.segment_index,
                    bbox=segment_patch.bbox,
                    source_path=source_path_local or record.source_path,
                    segments_dir=segments_dir,
                    method=record.segmentation_method,
                )
        finally:
            if source_path_local and source_path_local != record.source_path:
                shutil.rmtree(source_path_local.parent, ignore_errors=True)

        record.segments = [
            segment
            for _, segment in sorted(by_index.items())
            if segment.segment_index not in deleted
        ]
        return record

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _read_from_storage(self, key: str) -> bytes | None:
        if self._storage and self._storage.object_exists(key):
            import urllib.request

            url = self._storage.get_url(key)
            try:
                with urllib.request.urlopen(url) as resp:
                    return resp.read()
            except Exception:
                return None
        return None

    def _write_segment(
        self,
        *,
        image_id: str,
        segment_index: int,
        bbox: BoundingBox,
        source_path: Path,
        segments_dir: Path,
        method: str,
    ) -> Segment:
        crop_path = segments_dir / f"segment_{segment_index}.jpg"
        img = cv.imread(str(source_path))
        if img is not None:
            h, w = img.shape[:2]
            x1 = max(0, bbox.x)
            y1 = max(0, bbox.y)
            x2 = min(w, bbox.x + bbox.w)
            y2 = min(h, bbox.y + bbox.h)
            if x2 > x1 and y2 > y1:
                cv.imwrite(str(crop_path), img[y1:y2, x1:x2])
            else:
                shutil.copyfile(source_path, crop_path)
        else:
            shutil.copyfile(source_path, crop_path)

        return Segment(
            segment_id=f"{image_id}:{segment_index}",
            segment_index=segment_index,
            bbox=bbox,
            crop_url=f"/api/v1/images/{image_id}/segments/{segment_index}/crop",
            pipeline_url=f"/api/v1/images/{image_id}/pipeline?method={method}",
        )

    # ------------------------------------------------------------------
    # KMeans segmentation (reimplemented from research preprocessing/kmeans.py)
    # ------------------------------------------------------------------
    _CLUSTER_COLOURS = np.array(
        [
            (0, 80, 255),
            (255, 80, 80),
            (80, 220, 80),
            (220, 80, 220),
            (80, 220, 220),
        ],
        dtype=np.uint8,
    )

    @staticmethod
    def _odd_kernel(value: float, minimum: int, maximum: int) -> int:
        k = int(round(value))
        k = max(minimum, min(k, maximum))
        if k % 2 == 0:
            k += 1
        return min(k, maximum if maximum % 2 == 1 else maximum - 1)

    @staticmethod
    def _kmeans_bboxes(
        img: np.ndarray, out_path: Path | None = None
    ) -> list[BoundingBox]:
        h, w = img.shape[:2]
        side = min(h, w)
        working_size = min(max(side, 512), 1024)

        interpolation = (
            cv.INTER_AREA if side >= working_size else cv.INTER_LINEAR
        )
        small = cv.resize(
            img,
            (working_size, working_size),
            interpolation=interpolation,
        )

        # Median blur to flatten texture
        median_k = SegmentationPipeline._odd_kernel(working_size * 0.03, 15, 99)
        median_bgr = cv.medianBlur(small, median_k)

        # HSV + Gaussian blur
        hsv = cv.cvtColor(median_bgr, cv.COLOR_BGR2HSV)
        gauss_k = SegmentationPipeline._odd_kernel(working_size * 0.08, 31, 255)
        blur = cv.GaussianBlur(hsv, (gauss_k, gauss_k), 0)

        # Unblurred HSV for local K=2 shrink
        hsv_raw = cv.cvtColor(small, cv.COLOR_BGR2HSV)

        mask = SegmentationPipeline._plate_mask(small)
        mask_bool = mask.astype(bool)

        # Color clustering
        flat = blur.reshape(-1, 3).astype(np.float32)
        flat[~mask_bool.reshape(-1)] = np.array([1000.0] * 3, dtype=np.float32)

        n_clusters = 3
        labels = KMeans(
            n_clusters=n_clusters,
            random_state=0,
            n_init=10,
        ).fit_predict(flat)
        label_image = labels.reshape(small.shape[:2]).astype(np.int32)

        # Smart foreground label selection
        fg_label = SegmentationPipeline._choose_foreground_label(
            label_image, mask_bool, hsv
        )
        fg_mask = np.zeros(small.shape[:2], dtype=np.uint8)
        fg_mask[(label_image == fg_label) & mask_bool] = 255

        # Erode to core, then dilate back
        cleaned_fg = SegmentationPipeline._erode_to_core(fg_mask)
        if not np.any(cleaned_fg):
            cleaned_fg = fg_mask

        # Location-based clustering
        points = np.argwhere(cleaned_fg == 255).astype(np.int32)
        if len(points) == 0:
            return []

        cluster_count = min(3, len(points))
        if cluster_count == 1:
            loc_labels = np.zeros(len(points), dtype=np.int32)
        else:
            loc_labels = KMeans(
                n_clusters=cluster_count, random_state=0, n_init=10
            ).fit_predict(points.astype(np.float32))

        bboxes_raw = SegmentationPipeline._get_bbox(loc_labels.astype(np.int32), points)
        bboxes_raw.sort(key=lambda b: (b["ymin"], b["xmin"]))

        # Refine bboxes
        bboxes = SegmentationPipeline._refine_bboxes(
            bboxes_raw, cleaned_fg, hsv_raw, small
        )
        bboxes = bboxes[:3]

        sx, sy = w / working_size, h / working_size
        results: list[BoundingBox] = []
        for bb in bboxes:
            results.append(
                BoundingBox(
                    x=int(bb["xmin"] * sx),
                    y=int(bb["ymin"] * sy),
                    w=int((bb["xmax"] - bb["xmin"]) * sx),
                    h=int((bb["ymax"] - bb["ymin"]) * sy),
                )
            )

        if out_path and results:
            vis = small.copy()
            thickness = max(2, int(working_size * 0.005))
            for bb in bboxes:
                cv.rectangle(
                    vis,
                    (bb["xmin"], bb["ymin"]),
                    (bb["xmax"], bb["ymax"]),
                    (0, 255, 0),
                    thickness,
                )
            cv.imwrite(str(out_path), vis)

        return results

    @staticmethod
    def _contour_bboxes(
        img: np.ndarray, out_path: Path | None = None
    ) -> list[BoundingBox]:
        h, w = img.shape[:2]
        small = cv.resize(img, (256, 256))
        gray = cv.cvtColor(small, cv.COLOR_BGR2GRAY)
        edges = cv.Canny(gray, 50, 150)
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (7, 7))
        closed = cv.morphologyEx(edges, cv.MORPH_CLOSE, kernel)
        contours, _ = cv.findContours(closed, cv.RETR_EXTERNAL, cv.CHAIN_APPROX_SIMPLE)

        scored: list[tuple[float, int, int, int, int]] = []
        for cnt in contours:
            area = cv.contourArea(cnt)
            if area < 100:
                continue
            peri = cv.arcLength(cnt, True)
            if peri < 1:
                continue
            circularity = 4 * np.pi * area / (peri * peri)
            score = area * circularity
            x, y, bw, bh = cv.boundingRect(cnt)
            scored.append((score, x, y, bw, bh))

        scored.sort(key=lambda s: s[0], reverse=True)
        top = scored[:3]

        sx, sy = w / 256.0, h / 256.0
        results: list[BoundingBox] = []
        for _, bx, by, bw, bh in top:
            results.append(
                BoundingBox(
                    x=int(bx * sx),
                    y=int(by * sy),
                    w=int(bw * sx),
                    h=int(bh * sy),
                )
            )

        if out_path and results:
            vis = small.copy()
            for _, bx, by, bw, bh in top:
                cv.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
            cv.imwrite(str(out_path), vis)

        return results

    @staticmethod
    def _bbox_iou(a: BoundingBox, b: BoundingBox) -> float:
        ax2 = a.x + a.w
        ay2 = a.y + a.h
        bx2 = b.x + b.w
        by2 = b.y + b.h
        inter_x1 = max(a.x, b.x)
        inter_y1 = max(a.y, b.y)
        inter_x2 = min(ax2, bx2)
        inter_y2 = min(ay2, by2)
        if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
            return 0.0
        inter = float((inter_x2 - inter_x1) * (inter_y2 - inter_y1))
        union = float(a.w * a.h + b.w * b.h - inter)
        return inter / union if union > 0 else 0.0

    @staticmethod
    def _filter_non_overlapping_bboxes(
        bboxes: list[BoundingBox], iou_thresh: float = 0.25, max_boxes: int = 3
    ) -> list[BoundingBox]:
        kept: list[BoundingBox] = []
        for box in bboxes:
            if all(
                SegmentationPipeline._bbox_iou(box, kept_box) < iou_thresh
                for kept_box in kept
            ):
                kept.append(box)
            if len(kept) >= max_boxes:
                break
        return kept

    @staticmethod
    def _yolo_bboxes(
        img: np.ndarray, out_path: Path | None = None
    ) -> list[BoundingBox]:
        model = _get_yolo_model()
        if model is None:
            return SegmentationPipeline._kmeans_bboxes(img, out_path)
        h, w = img.shape[:2]
        from ultralytics.engine.results import Results as YOLOResults

        results: YOLOResults = model(  # type: ignore[call-overload,operator]
            img, verbose=False, conf=0.15, imgsz=640, end2end=False
        )
        if not results or results[0].boxes is None:
            return SegmentationPipeline._kmeans_bboxes(img, out_path)

        boxes = results[0].boxes.xyxy
        confs = results[0].boxes.conf
        if boxes is None or confs is None or len(boxes) == 0:
            return SegmentationPipeline._kmeans_bboxes(img, out_path)

        scored_bboxes: list[tuple[float, BoundingBox]] = []
        for conf_val, box_coords in zip(confs.tolist(), boxes.tolist(), strict=False):
            x1, y1, x2, y2 = map(int, box_coords)
            x1c = max(0, x1)
            y1c = max(0, y1)
            x2c = min(w, x2)
            y2c = min(h, y2)
            if x2c <= x1c or y2c <= y1c:
                continue
            scored_bboxes.append(
                (
                    float(conf_val),
                    BoundingBox(x=x1c, y=y1c, w=x2c - x1c, h=y2c - y1c),
                )
            )

        scored_bboxes.sort(key=lambda sb: sb[0], reverse=True)
        results_bboxes = SegmentationPipeline._filter_non_overlapping_bboxes(
            [bb for _, bb in scored_bboxes],
            iou_thresh=0.25,
            max_boxes=3,
        )

        if out_path and results_bboxes:
            vis = img.copy()
            thickness = max(2, int(max(h, w) * 0.005))
            for bb in results_bboxes:
                cv.rectangle(
                    vis,
                    (bb.x, bb.y),
                    (bb.x + bb.w, bb.y + bb.h),
                    (0, 255, 0),
                    thickness,
                )
            cv.imwrite(str(out_path), vis)

        return results_bboxes

    @staticmethod
    def _plate_mask(img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        radius = int(round(min(h, w) * 0.45))
        mask = np.zeros((h, w), dtype=np.uint8)
        cv.circle(mask, (w // 2, h // 2), radius, 255, -1)
        return mask

    @staticmethod
    def _choose_foreground_label(
        label_image: np.ndarray,
        mask_bool: np.ndarray,
        hsv_image: np.ndarray,
    ) -> int:
        inside = label_image[mask_bool]
        if inside.size == 0:
            return 0
        outside = label_image[~mask_bool]
        bg_label = -1
        if outside.size > 0:
            bg_label = int(np.bincount(outside).argmax())
        candidates = [int(lbl) for lbl in np.unique(inside) if int(lbl) != bg_label]
        if not candidates:
            candidates = [int(lbl) for lbl in np.unique(inside)]
        inside_total = len(inside)
        masked_hsv = hsv_image[mask_bool]
        preferred: list[tuple[float, int]] = []
        fallback: list[tuple[float, int]] = []
        for label in candidates:
            cluster_px = masked_hsv[inside == label]
            if len(cluster_px) == 0:
                continue
            area_frac = len(cluster_px) / inside_total
            v_score = float(np.percentile(cluster_px[:, 2], 95))
            s_score = float(np.percentile(cluster_px[:, 1], 75))
            score = v_score + 0.35 * s_score
            item = (score, label)
            if 0.005 <= area_frac <= 0.25:
                preferred.append(item)
            fallback.append(item)
        if preferred:
            return max(preferred)[1]
        if fallback:
            return max(fallback)[1]
        return candidates[0]

    @staticmethod
    def _erode_to_core(mask: np.ndarray) -> np.ndarray:
        size = max(mask.shape)
        close_sz = SegmentationPipeline._odd_kernel(size * 0.015, 3, 11)
        close_k = cv.getStructuringElement(cv.MORPH_ELLIPSE, (close_sz, close_sz))
        closed = cv.morphologyEx(mask, cv.MORPH_CLOSE, close_k, iterations=1)
        erode_sz = SegmentationPipeline._odd_kernel(size * 0.035, 5, 25)
        erode_k = cv.getStructuringElement(cv.MORPH_ELLIPSE, (erode_sz, erode_sz))
        eroded = cv.morphologyEx(closed, cv.MORPH_ERODE, erode_k, iterations=1)
        dilate_sz = SegmentationPipeline._odd_kernel(size * 0.025, 5, 21)
        dilate_k = cv.getStructuringElement(cv.MORPH_ELLIPSE, (dilate_sz, dilate_sz))
        return np.asarray(
            cv.morphologyEx(eroded, cv.MORPH_DILATE, dilate_k, iterations=1),
            dtype=np.uint8,
        )

    @staticmethod
    def _get_bbox(labels: np.ndarray, points: np.ndarray) -> list[dict[str, int]]:
        cluster_count = int(labels.max()) + 1 if labels.size else 0
        clusters: list[list[np.ndarray]] = [[] for _ in range(cluster_count)]
        for i, lbl in enumerate(labels):
            clusters[int(lbl)].append(points[i])
        bboxes: list[dict[str, int]] = []
        for cluster in clusters:
            if not cluster:
                continue
            cp = np.array(cluster, dtype=np.int32)
            bboxes.append(
                {
                    "xmin": int(np.min(cp[:, 1])),
                    "ymin": int(np.min(cp[:, 0])),
                    "xmax": int(np.max(cp[:, 1])),
                    "ymax": int(np.max(cp[:, 0])),
                }
            )
        return bboxes

    @staticmethod
    def _local_k2_shrink(
        bbox: dict[str, int],
        hsv_image: np.ndarray,
        original_bgr: np.ndarray,
    ) -> dict[str, int] | None:
        x1, y1, x2, y2 = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
        roi = hsv_image[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        v_ch = roi[:, :, 2].astype(np.float32).reshape(-1, 1)
        try:
            k2labels = KMeans(n_clusters=2, random_state=0, n_init=5).fit_predict(v_ch)
        except Exception:
            return None
        c0_mean = float(v_ch[k2labels == 0].mean())
        c1_mean = float(v_ch[k2labels == 1].mean())
        bright = 0 if c0_mean >= c1_mean else 1
        bright_mask = (k2labels == bright).reshape(roi.shape[:2]).astype(np.uint8) * 255
        contours, _ = cv.findContours(
            bright_mask,
            cv.RETR_EXTERNAL,
            cv.CHAIN_APPROX_SIMPLE,
        )
        if not contours:
            return None
        best = max(contours, key=cv.contourArea)
        cx, cy, cw, ch = cv.boundingRect(best)
        pad = max(2, int(max(x2 - x1, y2 - y1) * 0.02))
        return {
            "xmin": max(0, x1 + cx - pad),
            "ymin": max(0, y1 + cy - pad),
            "xmax": min(original_bgr.shape[1], x1 + cx + cw + pad),
            "ymax": min(original_bgr.shape[0], y1 + cy + ch + pad),
        }

    @staticmethod
    def _refine_bboxes(
        bboxes: list[dict[str, int]],
        mask: np.ndarray,
        hsv_image: np.ndarray,
        original_bgr: np.ndarray,
    ) -> list[dict[str, int]]:
        refined: list[dict[str, int]] = []
        for bbox in bboxes:
            x1, y1, x2, y2 = bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
            w = max(1, x2 - x1)
            h = max(1, y2 - y1)
            size = max(w, h)
            roi = mask[y1:y2, x1:x2].copy()
            k_sz = SegmentationPipeline._odd_kernel(size * 0.05, 3, 45)
            kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (k_sz, k_sz))
            eroded = cv.morphologyEx(roi, cv.MORPH_ERODE, kernel)
            contours, _ = cv.findContours(
                eroded,
                cv.RETR_EXTERNAL,
                cv.CHAIN_APPROX_SIMPLE,
            )
            if not contours:
                contours, _ = cv.findContours(
                    roi,
                    cv.RETR_EXTERNAL,
                    cv.CHAIN_APPROX_SIMPLE,
                )
            if not contours:
                refined.append(bbox)
                continue
            best_c = None
            max_score = -1.0
            for c in contours:
                area = cv.contourArea(c)
                bcx, bcy, bcw, bch = cv.boundingRect(c)
                bbox_area = max(1, bcw * bch)
                fill_ratio = area / float(bbox_area)
                fit = 1.0 - min(abs(fill_ratio - 0.785), 1.0)
                score = area * fit
                if score > max_score:
                    max_score = score
                    best_c = c
            if best_c is None:
                refined.append(bbox)
                continue
            bcx, bcy, bcw, bch = cv.boundingRect(best_c)
            best_fill = cv.contourArea(best_c) / float(max(1, bcw * bch))
            fit_score = 1.0 - min(abs(best_fill - 0.785), 1.0)
            if fit_score < 0.3 and hsv_image is not None and original_bgr is not None:
                shrunk = SegmentationPipeline._local_k2_shrink(
                    bbox,
                    hsv_image,
                    original_bgr,
                )
                if shrunk is not None:
                    refined.append(shrunk)
                    continue
            pad = (k_sz // 2) + int(size * 0.02)
            refined.append(
                {
                    "xmin": max(0, x1 + bcx - pad),
                    "ymin": max(0, y1 + bcy - pad),
                    "xmax": min(mask.shape[1], x1 + bcx + bcw + pad),
                    "ymax": min(mask.shape[0], y1 + bcy + bch + pad),
                }
            )
        refined.sort(key=lambda bb: (bb["ymin"], bb["xmin"]))
        return refined

    @staticmethod
    def _compose_pipeline(
        source: Path,
        prepared: Path,
        bbox: Path,
        out: Path,
    ) -> None:
        s = cv.imread(str(source))
        p = cv.imread(str(prepared))
        b = cv.imread(str(bbox))
        if s is None or p is None or b is None:
            return
        s = cv.resize(s, (256, 256))
        p = cv.resize(p, (256, 256))
        b = cv.resize(b, (256, 256))
        panel = np.hstack([s, p, b])
        cv.imwrite(str(out), panel)
