from pathlib import Path

import cv2
import numpy as np

from src.analysis.dataset_eda import (
    HeatmapStyle,
    build_dataset_eda_report,
    build_species_environment_matrix,
    render_species_environment_heatmap,
)


def _write_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = np.full((32, 32, 3), 150, dtype=np.uint8)
    cv2.imwrite(str(path), image)



def test_build_dataset_eda_report_summarizes_each_collection(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "Dataset"
    curated_root = dataset_root / "curated_primary"
    incoming_root = dataset_root / "incoming_low_quality"
    mapping_path = dataset_root / "strain_to_specy.csv"

    _write_image(
        curated_root
        / "DTO 148-D1 Penicillium polonicum"
        / "DTO 148-D1 MEAob_edited.jpg"
    )
    _write_image(incoming_root / "Aspergillus section" / "unknown_file.jpg")
    mapping_path.write_text("Strain,Species\nDTO 148-D1,Penicillium polonicum\n")

    monkeypatch.setattr(
        "src.prepare.dataset.SOURCE_COLLECTIONS",
        {
            "curated": {
                "display_name": "curated_primary",
                "quality_tier": "curated",
                "path": curated_root,
            },
            "incoming": {
                "display_name": "incoming_low_quality",
                "quality_tier": "incoming",
                "path": incoming_root,
            },
        },
    )
    monkeypatch.setattr("src.prepare.dataset.STRAIN_SPECIES_MAPPING_PATH", mapping_path)
    monkeypatch.setattr(
        "src.analysis.dataset_eda.SOURCE_COLLECTIONS",
        {
            "curated": {
                "display_name": "curated_primary",
                "quality_tier": "curated",
                "path": curated_root,
            },
            "incoming": {
                "display_name": "incoming_low_quality",
                "quality_tier": "incoming",
                "path": incoming_root,
            },
        },
    )

    report = build_dataset_eda_report(["curated", "incoming"])

    assert report.total_images == 2
    assert report.total_species == 2
    assert len(report.collections) == 2
    assert report.collections[0].collection_key == "curated"
    assert report.collections[0].species_image_counts == {"Penicillium polonicum": 1}
    assert report.collections[0].species_environment_counts == {"Penicillium polonicum::MEA": 1}
    assert report.collections[1].species_image_counts == {"Aspergillus section": 1}


def test_render_species_environment_heatmap_uses_large_font_style(monkeypatch, tmp_path: Path) -> None:
    dataset_root = tmp_path / "Dataset"
    curated_root = dataset_root / "curated_primary"
    mapping_path = dataset_root / "strain_to_specy.csv"

    _write_image(
        curated_root
        / "DTO 148-D1 Penicillium polonicum"
        / "DTO 148-D1 MEAob_edited.jpg"
    )
    mapping_path.write_text("Strain,Species\nDTO 148-D1,Penicillium polonicum\n")

    monkeypatch.setattr(
        "src.prepare.dataset.SOURCE_COLLECTIONS",
        {
            "curated": {
                "display_name": "curated_primary",
                "quality_tier": "curated",
                "path": curated_root,
            },
        },
    )
    monkeypatch.setattr("src.prepare.dataset.STRAIN_SPECIES_MAPPING_PATH", mapping_path)
    monkeypatch.setattr(
        "src.analysis.dataset_eda.SOURCE_COLLECTIONS",
        {
            "curated": {
                "display_name": "curated_primary",
                "quality_tier": "curated",
                "path": curated_root,
            },
        },
    )

    report = build_dataset_eda_report(["curated"])
    species_names, environments, matrix = build_species_environment_matrix(report, max_species=8)
    output_path = tmp_path / "heatmap.png"
    style = HeatmapStyle(tick_label_size=28, annotation_size=24)

    render_species_environment_heatmap(species_names, environments, matrix, output_path, style=style)

    assert output_path.exists()
    assert species_names == ["Penicillium polonicum"]
    assert environments == ["MEA"]
    assert matrix.shape == (1, 1)
    assert matrix[0, 0] == 1
