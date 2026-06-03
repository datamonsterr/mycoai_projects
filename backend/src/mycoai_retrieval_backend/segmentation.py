from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

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
        pipeline_path = artifact_dir / f"pipeline_{method}.jpg"
        shutil.copyfile(stored_source, pipeline_path)
        bbox_path = artifact_dir / f"bbox_{method}.jpg"
        shutil.copyfile(stored_source, bbox_path)

        bboxes = self._initial_bboxes(stored_source.stat().st_size)
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
        shutil.copyfile(source_path, crop_path)
        return Segment(
            segment_id=f"{image_id}:{segment_index}",
            segment_index=segment_index,
            bbox=bbox,
            crop_url=f"/api/v1/images/{image_id}/segments/{segment_index}/crop",
            pipeline_url=f"/api/v1/images/{image_id}/pipeline?method={method}",
        )

    @staticmethod
    def _initial_bboxes(file_size: int) -> list[BoundingBox]:
        offset = file_size % 17
        return [
            BoundingBox(x=48 + offset, y=52, w=72, h=72),
            BoundingBox(x=136, y=88 + offset, w=68, h=68),
            BoundingBox(x=92, y=148, w=64, h=64),
        ]
