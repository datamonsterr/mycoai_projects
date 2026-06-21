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
    ) -> ImageRecord:
        if method not in ALLOWED_METHODS:
            raise ValueError(f"unsupported segmentation method: {method}")

        image_id = uuid4().hex
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

            return ImageRecord(
                image_id=image_id,
                source_path=(Path(prefix) / "source.jpg" if self._use_storage else stored_source),
                artifact_dir=(Path(prefix) if self._use_storage else artifact_dir),
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
    # KMeans segmentation
    # ------------------------------------------------------------------
    @staticmethod
    def _kmeans_bboxes(
        img: np.ndarray, out_path: Path | None = None
    ) -> list[BoundingBox]:
        h, w = img.shape[:2]

        small = cv.resize(img, (256, 256))
        mask = SegmentationPipeline._plate_mask(small)
        hsv = cv.cvtColor(small, cv.COLOR_BGR2HSV)

        masked_pixels = hsv[mask > 0].astype(np.float32)
        if len(masked_pixels) < 10:
            return []

        kmeans = KMeans(n_clusters=3, random_state=0, n_init=5)
        labels = kmeans.fit_predict(masked_pixels)
        centers = kmeans.cluster_centers_

        bg_label = int(np.argmin(centers[:, 2]))
        fg_mask: np.ndarray = np.zeros((256, 256), dtype=np.uint8)
        selection = labels != bg_label
        fg_mask[mask > 0] = selection.astype(np.uint8) * 255

        kernel = cv.getStructuringElement(cv.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv.morphologyEx(fg_mask, cv.MORPH_CLOSE, kernel)
        fg_mask = cv.morphologyEx(fg_mask, cv.MORPH_OPEN, kernel)

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
