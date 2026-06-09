from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import cv2 as cv
import numpy as np
from sklearn.cluster import KMeans  # type: ignore[import-untyped]

from .image_models import BoundingBox, ImageRecord, Segment, SegmentPatchRequest

ALLOWED_METHODS = {"kmeans", "contour"}


class ImageStore:
    def __init__(self, upload_root: Path) -> None:
        self.upload_root = upload_root
        self._records: dict[str, ImageRecord] = {}

    def add(self, record: ImageRecord) -> None:
        self._records[record.image_id] = record

    def get(self, image_id: str) -> ImageRecord | None:
        return self._records.get(image_id)


class SegmentationPipeline:
    def __init__(self, upload_root: Path) -> None:
        self.upload_root = upload_root

    def segment_upload(
        self,
        source_path: Path,
        *,
        strain: str,
        media: str,
        method: str = "kmeans",
    ) -> ImageRecord:
        if method not in ALLOWED_METHODS:
            raise ValueError(f"unsupported segmentation method: {method}")

        image_id = uuid4().hex
        artifact_dir = self.upload_root / strain / media / image_id
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

        return ImageRecord(
            image_id=image_id,
            source_path=stored_source,
            artifact_dir=artifact_dir,
            source_url=f"/static/{strain}/{media}/{image_id}/source.jpg",
            segments=segments,
            segmentation_method=method,
        )

    def update_segments(
        self,
        record: ImageRecord,
        patch: SegmentPatchRequest,
    ) -> ImageRecord:
        deleted = set(patch.deleted_segments)
        by_index = {segment.segment_index: segment for segment in record.segments}

        for segment_patch in patch.segments:
            if segment_patch.segment_index in deleted:
                continue
            by_index[segment_patch.segment_index] = self._write_segment(
                image_id=record.image_id,
                segment_index=segment_patch.segment_index,
                bbox=segment_patch.bbox,
                source_path=record.source_path,
                segments_dir=record.artifact_dir / "segments",
                method=record.segmentation_method,
            )

        record.segments = [
            segment
            for _, segment in sorted(by_index.items())
            if segment.segment_index not in deleted
        ]
        return record

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
    # KMeans segmentation (reimplemented from research/src/preprocessing/kmeans.py)
    # ------------------------------------------------------------------
    @staticmethod
    def _kmeans_bboxes(
        img: np.ndarray, out_path: Path | None = None
    ) -> list[BoundingBox]:
        h, w = img.shape[:2]

        # Preprocess: reduce to 256x256 for speed, create plate mask
        small = cv.resize(img, (256, 256))
        mask = SegmentationPipeline._plate_mask(small)
        hsv = cv.cvtColor(small, cv.COLOR_BGR2HSV)

        # K=3 on HSV pixels inside mask
        masked_pixels = hsv[mask > 0].astype(np.float32)
        if len(masked_pixels) < 10:
            return []

        kmeans = KMeans(n_clusters=3, random_state=0, n_init=5)
        labels = kmeans.fit_predict(masked_pixels)
        centers = kmeans.cluster_centers_

        # Darkness: pick darkest cluster as background (lowest V)
        bg_label = int(np.argmin(centers[:, 2]))
        fg_mask: np.ndarray = np.zeros((256, 256), dtype=np.uint8)
        selection = labels != bg_label
        fg_mask[mask > 0] = selection.astype(np.uint8) * 255

        # Clean up
        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv.morphologyEx(fg_mask, cv.MORPH_CLOSE, kernel)
        fg_mask = cv.morphologyEx(fg_mask, cv.MORPH_OPEN, kernel)

        # Find connected components → bounding boxes
        num_labels, label_map, stats, _ = cv.connectedComponentsWithStats(
            fg_mask, connectivity=8
        )
        bboxes_raw: list[tuple[int, int, int, int, int]] = []
        for i in range(1, num_labels):
            area = stats[i, cv.CC_STAT_AREA]
            if area < 200:
                continue
            x, y, bw, bh = (
                stats[i, cv.CC_STAT_LEFT],
                stats[i, cv.CC_STAT_TOP],
                stats[i, cv.CC_STAT_WIDTH],
                stats[i, cv.CC_STAT_HEIGHT],
            )
            bboxes_raw.append((area, x, y, bw, bh))

        bboxes_raw.sort(key=lambda b: b[0], reverse=True)
        top = bboxes_raw[:3]

        # Scale back to original dimensions
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

        # Draw bbox visualization
        if out_path and results:
            vis = small.copy()
            for _, bx, by, bw, bh in top:
                cv.rectangle(vis, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
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
    def _plate_mask(img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        radius = int(round(min(h, w) * 0.45))
        mask = np.zeros((h, w), dtype=np.uint8)
        cv.circle(mask, (w // 2, h // 2), radius, 255, -1)
        return mask

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
