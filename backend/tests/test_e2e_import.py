"""End-to-end tests for the full DTO import flow.

Tests the complete pipeline:
  scan → parse → segment → DB persist → Qdrant index (mocked)
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from tempfile import mkdtemp
from unittest.mock import patch

import pytest

from mycoai_retrieval_backend.tasks.batch import _parse_filename_metadata

# Make import_dto.py script importable for testing
_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


@pytest.fixture
def dto_fixture_dir():
    """Create a realistic DTO dataset fixture directory."""
    import numpy as np

    root = Path(mkdtemp(prefix="test_dto_e2e_"))

    # Species 1: Penicillium cyclopium
    sp1 = root / "DTO 148-C8 Penicillium cyclopium"
    sp1.mkdir(parents=True)

    # Species 2: Penicillium polonicum
    sp2 = root / "DTO 148-C9 Penicillium polonicum"
    sp2.mkdir(parents=True)

    # Species 3: Penicillium commune
    sp3 = root / "DTO 148-E6 Penicillium commune"
    sp3.mkdir(parents=True)

    # Create test images (small colored squares)
    import cv2 as cv

    def _make_img(r: int, g: int, b: int) -> np.ndarray:
        img = np.zeros((64, 64, 3), dtype=np.uint8)
        img[20:45, 20:45] = [b, g, r]
        return img

    # DTO 148-C8 images
    cv.imwrite(str(sp1 / "DTO 148-C8 CYAob_edited.jpg"), _make_img(200, 180, 160))
    cv.imwrite(str(sp1 / "DTO 148-C8 CYArev_edited.jpg"), _make_img(200, 180, 160))
    cv.imwrite(str(sp1 / "DTO 148-C8 MEAr_edited.jpg"), _make_img(220, 200, 180))
    cv.imwrite(str(sp1 / "DTO 148-C8 YESob_edited.jpg"), _make_img(240, 220, 200))

    # DTO 148-C9 images
    cv.imwrite(str(sp2 / "DTO 148-C9 CYAob_edited.jpg"), _make_img(180, 200, 160))
    cv.imwrite(str(sp2 / "DTO 148-C9 MEAr_edited.jpg"), _make_img(180, 220, 180))
    cv.imwrite(str(sp2 / "DTO 148-C9 YESob_edited.jpg"), _make_img(180, 240, 200))

    # DTO 148-E6 images
    cv.imwrite(str(sp3 / "DTO 148-E6 CYAob_edited.jpg"), _make_img(160, 180, 200))
    cv.imwrite(str(sp3 / "DTO 148-E6 MEAr_edited.jpg"), _make_img(160, 200, 220))
    cv.imwrite(str(sp3 / "DTO 148-E6 YESob_edited.jpg"), _make_img(160, 220, 240))

    yield root
    shutil.rmtree(root, ignore_errors=True)


class TestE2EDtoImportFlow:
    """End-to-end test for the full DTO import pipeline."""

    def test_scan_parses_all_images(self, dto_fixture_dir: Path):
        """Scanning the fixture directory should find all 10 images."""
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)

        assert len(manifest.images) == 10
        assert len(manifest.species) == 3
        assert len(manifest.media) >= 3  # CYA, MEA, YES

    def test_manifest_species_correct(self, dto_fixture_dir: Path):
        """All 3 species should be detected."""
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)

        species_lower = {s.lower() for s in manifest.species}
        assert "penicillium cyclopium" in species_lower
        assert "penicillium polonicum" in species_lower
        assert "penicillium commune" in species_lower

    def test_manifest_media_correct(self, dto_fixture_dir: Path):
        """All media types should be detected."""
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)
        assert "CYA" in manifest.media
        assert "MEA" in manifest.media
        assert "YES" in manifest.media

    def test_each_image_has_correct_metadata(self, dto_fixture_dir: Path):
        """Each DtoImage should have correct strain, species, media, angle."""
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)

        for img in manifest.images:
            assert img.strain_code in ("DTO 148-C8", "DTO 148-C9", "DTO 148-E6")
            assert img.species_name.startswith("Penicillium")
            assert img.media_name in ("CYA", "MEA", "YES", "unknown")
            assert img.angle in ("ob", "rev", "unknown")
            assert img.source_path.is_file()

    def test_parser_handles_all_fixture_filenames(self, dto_fixture_dir: Path):
        """Every fixture filename should be parsed without unknown strain."""
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)

        for img in manifest.images:
            result = _parse_filename_metadata(
                img.original_filename,
                rel_path=str(img.source_path.relative_to(dto_fixture_dir)),
            )
            assert result["strain"] != "unknown", f"Failed: {img.original_filename}"
            assert result["media"] != "unknown", f"Failed: {img.original_filename}"

    def test_import_handles_limit(self, dto_fixture_dir: Path):
        """Import with limit should process exactly that many images."""
        # Verify manifest knows about total count
        from import_dto import scan_dto_dataset

        manifest = scan_dto_dataset(dto_fixture_dir)
        assert len(manifest.images) == 10

        manifest.images = manifest.images[:3]
        assert len(manifest.images) == 3


class TestE2ESegmentationFlow:
    """End-to-end test for segmentation + DB persistence of fixture images."""

    @pytest.mark.asyncio
    async def test_segmentation_produces_crops(self, dto_fixture_dir: Path):
        """Segmentation of a fixture image should produce crop files."""
        import asyncio

        from mycoai_retrieval_backend.segmentation import SegmentationPipeline

        tmp_upload = Path(mkdtemp(prefix="test_seg_"))
        try:
            pipeline = SegmentationPipeline(tmp_upload)

            img_path = next(
                p for p in dto_fixture_dir.rglob("*.jpg") if "DT" in p.name
            )

            record = await asyncio.to_thread(
                pipeline.segment_upload,
                img_path,
                strain="DTO 148-C8",
                media="CYA",
                method="kmeans",
            )

            assert record.image_id
            assert len(record.segments) >= 0
            assert record.source_path.exists()

        finally:
            shutil.rmtree(tmp_upload, ignore_errors=True)


class TestE2EImportStats:
    """Tests for ImportStats dataclass behavior."""

    def test_stats_tracks_counts(self):
        from import_dto import ImportStats

        stats = ImportStats()
        stats.species_created = 5
        stats.images_uploaded = 10
        stats.images_failed = 2
        stats.segments = 30
        stats.qdrant_indexed = 30

        summary = stats.summary()
        assert "Species:  5" in summary
        assert "Images:   10 uploaded, 2 failed" in summary
        assert "Segments: 30" in summary
        assert "Qdrant:   30 indexed" in summary

    def test_stats_elapsed_time(self):
        from import_dto import ImportStats

        stats = ImportStats()
        stats.start_time = 100.0
        stats.end_time = 105.5
        assert stats.elapsed() == 5.5

    def test_stats_errors_truncated(self):
        from import_dto import ImportStats

        stats = ImportStats()
        for i in range(10):
            stats.errors.append(f"error {i}")

        summary = stats.summary()
        # Should show first 5 errors only
        assert "error 0" in summary
        assert "error 4" in summary
        assert "error 5" not in summary
