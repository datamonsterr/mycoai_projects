import json
from pathlib import Path

from src.utils.build_fold_manifests import build_fold_manifest_rows, write_fold_manifests


def test_build_fold_manifest_rows_excludes_test_strains_from_train_pool(tmp_path: Path) -> None:
    mapping_csv = tmp_path / "strain_to_specy.csv"
    mapping_csv.write_text(
        "Strain,Species,Test\n"
        "S1,Species A,False\n"
        "S2,Species A,False\n"
        "S3,Species B,False\n"
        "S4,Species B,False\n"
    )

    segments_json = tmp_path / "prepared_segments_metadata.json"
    segments_json.write_text(
        json.dumps(
            [
                {"id": "img1", "data": {"strain": "S1", "specy": "Species A", "environment": "MEA"}},
                {"id": "img2", "data": {"strain": "S2", "specy": "Species A", "environment": "CYA"}},
                {"id": "img3", "data": {"strain": "S3", "specy": "Species B", "environment": "MEA"}},
                {"id": "img4", "data": {"strain": "S4", "specy": "Species B", "environment": "CYA"}},
            ]
        )
    )

    rows = build_fold_manifest_rows(
        source_csv=mapping_csv,
        segments_metadata_path=segments_json,
        n_folds=2,
    )

    assert rows
    for row in rows:
        assert row["test_strain"] not in row["train_strains"]


def test_build_fold_manifest_rows_collects_query_images_and_media(tmp_path: Path) -> None:
    mapping_csv = tmp_path / "strain_to_specy.csv"
    mapping_csv.write_text(
        "Strain,Species,Test\n"
        "S1,Species A,False\n"
        "S2,Species B,False\n"
    )

    segments_json = tmp_path / "prepared_segments_metadata.json"
    segments_json.write_text(
        json.dumps(
            [
                {"id": "img1", "data": {"strain": "S1", "specy": "Species A", "environment": "MEA"}},
                {"id": "img2", "data": {"strain": "S1", "specy": "Species A", "environment": "CYA"}},
                {"id": "img3", "data": {"strain": "S2", "specy": "Species B", "environment": "MEA"}},
            ]
        )
    )

    rows = build_fold_manifest_rows(
        source_csv=mapping_csv,
        segments_metadata_path=segments_json,
        n_folds=1,
    )

    species_a = next(row for row in rows if row["test_strain"] == "S1")
    assert species_a["query_count"] == 2
    assert species_a["query_image_ids"] == ["img1", "img2"]
    assert species_a["query_media"] == ["CYA", "MEA"]


def test_write_fold_manifests_writes_json_and_summary(tmp_path: Path) -> None:
    mapping_csv = tmp_path / "strain_to_specy.csv"
    mapping_csv.write_text(
        "Strain,Species,Test\n"
        "S1,Species A,False\n"
        "S2,Species B,False\n"
    )

    segments_json = tmp_path / "prepared_segments_metadata.json"
    segments_json.write_text(
        json.dumps(
            [
                {"id": "img1", "data": {"strain": "S1", "specy": "Species A", "environment": "MEA"}},
                {"id": "img2", "data": {"strain": "S2", "specy": "Species B", "environment": "CYA"}},
            ]
        )
    )

    output_dir = tmp_path / "folds"
    written = write_fold_manifests(
        output_dir=output_dir,
        source_csv=mapping_csv,
        segments_metadata_path=segments_json,
        n_folds=1,
    )

    assert len(written) == 2
    assert (output_dir / "fold_manifest_summary.csv").exists()
