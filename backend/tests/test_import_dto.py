"""Unit tests for DTO metadata parser and batch import logic."""

from __future__ import annotations

from backend.tasks.batch import _parse_filename_metadata


class TestMetadataParser:
    """Tests for _parse_filename_metadata covering all filename formats."""

    # ---------------------------------------------------------------
    # DTO format filenames
    # ---------------------------------------------------------------

    def test_dto_format_cya_obverse(self):
        """DTO 148-C8 CYAob_edited.jpg → DTO 148-C8, penicillium cyclopium, CYA, ob"""
        result = _parse_filename_metadata(
            "DTO 148-C8 CYAob_edited.jpg",
            rel_path="DTO 148-C8 Penicillium cyclopium/DTO 148-C8 CYAob_edited.jpg",
        )
        assert result["strain"] == "DTO 148-C8"
        assert result["media"] == "CYA"
        assert result["angle"] == "ob"

    def test_dto_format_mea_reverse(self):
        """DTO 148-C9 MEAr_edited.jpg → DTO 148-C9, MEA, rev"""
        result = _parse_filename_metadata(
            "DTO 148-C9 MEAr_edited.jpg",
            rel_path="DTO 148-C9 Penicillium polonicum/DTO 148-C9 MEAr_edited.jpg",
        )
        assert result["strain"] == "DTO 148-C9"
        assert result["media"] == "MEA"
        assert result["angle"] == "rev"

    def test_dto_format_yes_obverse(self):
        """DTO 148-E6 YESob_edited.jpg"""
        result = _parse_filename_metadata(
            "DTO 148-E6 YESob_edited.jpg",
            rel_path="DTO 148-E6 Penicillium commune/DTO 148-E6 YESob_edited.jpg",
        )
        assert result["strain"] == "DTO 148-E6"
        assert result["media"] == "YES"
        assert result["angle"] == "ob"

    def test_dto_format_cya30_normalized(self):
        """CYA30ob → CYA, ob"""
        result = _parse_filename_metadata("DTO 148-C8 CYA30ob_edited.jpg")
        assert result["media"] == "CYA"
        assert result["angle"] == "ob"

    def test_dto_format_cyas_normalized(self):
        """CYASrev → CYA, rev"""
        result = _parse_filename_metadata("DTO 148-C8 CYASrev_edited.jpg")
        assert result["media"] == "CYA"
        assert result["angle"] == "rev"

    def test_dto_format_dg18(self):
        """DG18ob_edited.jpg"""
        result = _parse_filename_metadata("DTO 148-D1 DG18ob_edited.jpg")
        assert result["media"] == "DG18"
        assert result["angle"] == "ob"

    def test_dto_format_crea(self):
        """CREAob_edited.jpg"""
        result = _parse_filename_metadata("DTO 148-D1 CREAob_edited.jpg")
        assert result["media"] == "CREA"
        assert result["angle"] == "ob"

    def test_dto_species_from_folder_path(self):
        """Species extracted from DTO folder path."""
        result = _parse_filename_metadata(
            "DTO 148-C8 CYAob_edited.jpg",
            rel_path="DTO 148-C8 Penicillium cyclopium/DTO 148-C8 CYAob_edited.jpg",
        )
        assert "penicillium" in result["species"].lower()

    # ---------------------------------------------------------------
    # CBS/IBT/T-number format filenames
    # ---------------------------------------------------------------

    def test_cbs_format(self):
        """formosanum CBS 101028 CYAo.jpg"""
        result = _parse_filename_metadata("formosanum CBS 101028 CYAo.jpg")
        assert result["strain"] == "CBS 101028"
        assert result["media"] == "CYA"
        assert result["angle"] == "ob"
        assert "formosanum" in result["species"]

    def test_ibt_format(self):
        """nordicum IBT 5105 MEAr.jpg"""
        result = _parse_filename_metadata("nordicum IBT 5105 MEAr.jpg")
        assert result["strain"] == "IBT 5105"
        assert result["media"] == "MEA"
        assert result["angle"] == "rev"

    def test_t_number_format(self):
        """T491 MEA rev.JPG"""
        result = _parse_filename_metadata("T491 MEA rev.JPG")
        assert result["strain"] == "T491"
        assert result["media"] == "MEA"
        assert result["angle"] == "rev"

    def test_nrrl_format(self):
        """NRRL 12345 CYAo.jpg"""
        result = _parse_filename_metadata("NRRL 12345 CYAo.jpg")
        assert result["strain"] == "NRRL 12345"
        assert result["media"] == "CYA"
        assert result["angle"] == "ob"

    # ---------------------------------------------------------------
    # Space-separated MEDIA ANGLE format
    # ---------------------------------------------------------------

    def test_space_separated_media_angle(self):
        """species MEA rev.jpg"""
        result = _parse_filename_metadata("species MEA rev.jpg")
        assert result["media"] == "MEA"
        assert result["angle"] == "rev"

    def test_space_separated_cya_ob(self):
        """species CYA ob.jpg"""
        result = _parse_filename_metadata("species CYA ob.jpg")
        assert result["media"] == "CYA"
        assert result["angle"] == "ob"

    # ---------------------------------------------------------------
    # Unknown / fallback cases
    # ---------------------------------------------------------------

    def test_no_media_info(self):
        """Filename without media info → unknown media/angle."""
        result = _parse_filename_metadata("some_image.jpg")
        assert result["media"] == "unknown"
        assert result["angle"] == "unknown"

    def test_folder_fallback_two_levels(self):
        """Fallback: species/strain/file.jpg → species from filename if metadata present."""
        result = _parse_filename_metadata(
            "DTO 148-C8 CYAo.jpg",
            rel_path="Penicillium commune/DTO 148-C8/DTO 148-C8 CYAo.jpg",
        )
        assert result["strain"] == "DTO 148-C8"
        assert result["media"] == "CYA"

    def test_folder_fallback_one_level(self):
        """Fallback: species/file.jpg with DTO metadata in filename."""
        result = _parse_filename_metadata(
            "DTO 148-C8 CYAo.jpg",
            rel_path="Penicillium cyclopium/DTO 148-C8 CYAo.jpg",
        )
        assert result["strain"] == "DTO 148-C8"
        assert result["media"] == "CYA"

    def test_strain_code_case_normalization(self):
        """Strain codes are uppercased."""
        result = _parse_filename_metadata("dto 148-c8 cyao.jpg")
        assert result["strain"] == "DTO 148-C8"
        assert result["media"] == "CYA"

    def test_edited_suffix_stripped(self):
        """_edited suffix removed from species detection area."""
        result = _parse_filename_metadata(
            "DTO 148-C8 YESo_edited.jpg",
            rel_path="DTO 148-C8 Penicillium commune/DTO 148-C8 YESo_edited.jpg",
        )
        assert result["strain"] == "DTO 148-C8"
        assert result["media"] == "YES"

    # ---------------------------------------------------------------
    # Edge cases
    # ---------------------------------------------------------------

    def test_empty_filename(self):
        result = _parse_filename_metadata("")
        assert result["species"] == "unknown"
        assert result["strain"] == "unknown"

    def test_uppercase_media_codes(self):
        """Media codes always uppercase output."""
        result = _parse_filename_metadata("DTO 148-C8 cyaob.jpg")
        assert result["media"] == "CYA"

    def test_mixed_case_strain(self):
        result = _parse_filename_metadata("Dto 148-C8 CYAo.jpg")
        assert result["strain"] == "DTO 148-C8"
