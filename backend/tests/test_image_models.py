import pytest
from pydantic import ValidationError

from backend.image_models import (
    BoundingBox,
    ImageRecord,
    ImageResponse,
    Segment,
    SegmentPatch,
    SegmentPatchRequest,
)


class TestBoundingBox:
    def test_valid(self) -> None:
        bb = BoundingBox(x=10, y=20, w=100, h=200)
        assert bb.x == 10
        assert bb.y == 20
        assert bb.w == 100
        assert bb.h == 200

    def test_zero_position(self) -> None:
        bb = BoundingBox(x=0, y=0, w=1, h=1)
        assert bb.x == 0
        assert bb.y == 0

    def test_negative_x_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=-1, y=0, w=10, h=10)

    def test_negative_y_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=-1, w=10, h=10)

    def test_zero_w_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, w=0, h=10)

    def test_zero_h_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, w=10, h=0)

    def test_negative_w_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, w=-1, h=10)

    def test_negative_h_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(x=0, y=0, w=10, h=-1)

    def test_missing_x_raises(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(y=0, w=10, h=10)  # type: ignore[arg-type]


class TestSegment:
    def test_valid(self) -> None:
        bb = BoundingBox(x=0, y=0, w=50, h=50)
        seg = Segment(
            segment_id="seg-1",
            segment_index=0,
            bbox=bb,
            crop_url="/crops/1.jpg",
            pipeline_url="/pipeline/1.jpg",
        )
        assert seg.segment_id == "seg-1"
        assert seg.segment_index == 0
        assert seg.bbox.w == 50
        assert seg.crop_url == "/crops/1.jpg"

    def test_negative_segment_index_raises(self) -> None:
        bb = BoundingBox(x=0, y=0, w=10, h=10)
        with pytest.raises(ValidationError):
            Segment(
                segment_id="s",
                segment_index=-1,
                bbox=bb,
                crop_url="c",
                pipeline_url="p",
            )


class TestImageRecord:
    def test_valid(self) -> None:
        from pathlib import Path

        bb = BoundingBox(x=0, y=0, w=10, h=10)
        seg = Segment(
            segment_id="s1",
            segment_index=0,
            bbox=bb,
            crop_url="c",
            pipeline_url="p",
        )
        record = ImageRecord(
            image_id="img-1",
            source_path=Path("/tmp/img.jpg"),
            artifact_dir=Path("/tmp/artifacts"),
            source_url="/images/1.jpg",
            segments=[seg],
            segmentation_method="kmeans",
        )
        assert record.image_id == "img-1"
        assert record.segmentation_method == "kmeans"
        assert len(record.segments) == 1


class TestImageResponse:
    def test_valid(self) -> None:
        bb = BoundingBox(x=0, y=0, w=10, h=10)
        seg = Segment(
            segment_id="s1",
            segment_index=0,
            bbox=bb,
            crop_url="c",
            pipeline_url="p",
        )
        resp = ImageResponse(
            image_id="img-1",
            source_url="/images/1.jpg",
            segments=[seg],
            segmentation_method="kmeans",
        )
        assert resp.image_id == "img-1"
        assert resp.segmentation_method == "kmeans"

    def test_model_validate_from_dict(self) -> None:
        data = {
            "image_id": "img-1",
            "source_url": "/images/1.jpg",
            "segments": [],
            "segmentation_method": "threshold",
        }
        resp = ImageResponse.model_validate(data)
        assert resp.image_id == "img-1"
        assert resp.segments == []


class TestSegmentPatch:
    def test_valid(self) -> None:
        bb = BoundingBox(x=10, y=20, w=50, h=60)
        patch = SegmentPatch(segment_index=3, bbox=bb)
        assert patch.segment_index == 3
        assert patch.bbox.x == 10

    def test_negative_index_raises(self) -> None:
        bb = BoundingBox(x=0, y=0, w=10, h=10)
        with pytest.raises(ValidationError):
            SegmentPatch(segment_index=-1, bbox=bb)


class TestSegmentPatchRequest:
    def test_defaults(self) -> None:
        req = SegmentPatchRequest()
        assert req.segments == []
        assert req.deleted_segments == []

    def test_with_segments(self) -> None:
        bb = BoundingBox(x=0, y=0, w=10, h=10)
        patch = SegmentPatch(segment_index=0, bbox=bb)
        req = SegmentPatchRequest(segments=[patch])
        assert len(req.segments) == 1
        assert req.deleted_segments == []

    def test_with_deleted(self) -> None:
        req = SegmentPatchRequest(deleted_segments=[0, 1, 2])
        assert len(req.deleted_segments) == 3
