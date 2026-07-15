from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from src.config import SOURCE_COLLECTIONS
from src.prepare.dataset import (
    load_source_collections,
    parse_source_metadata,
    resolve_source_collection_names,
    iter_source_images,
    load_strain_species_mapping,
)


@dataclass(frozen=True)
class DatasetCollectionSummary:
    collection_key: str
    display_name: str
    quality_tier: str
    source_root: str
    image_count: int
    species_count: int
    strain_count: int
    environment_count: int
    parse_status_counts: dict[str, int]
    species_image_counts: dict[str, int]
    strain_image_counts: dict[str, int]
    environment_image_counts: dict[str, int]
    species_environment_counts: dict[str, int]


@dataclass(frozen=True)
class DatasetEdaReport:
    collections: list[DatasetCollectionSummary]
    total_images: int
    total_species: int
    total_strains: int
    total_environments: int


@dataclass(frozen=True)
class HeatmapStyle:
    figure_size: tuple[float, float] = (14, 9.5)
    title_size: int = 34
    axis_label_size: int = 30
    tick_label_size: int = 28
    annotation_size: int = 24
    colorbar_label_size: int = 28
    colorbar_tick_size: int = 24


def build_dataset_collection_summary(collection_key: str) -> DatasetCollectionSummary:
    collections = load_source_collections()
    collection = collections[collection_key]
    strain_species_mapping = load_strain_species_mapping()
    species_counts: Counter[str] = Counter()
    strain_counts: Counter[str] = Counter()
    environment_counts: Counter[str] = Counter()
    parse_status_counts: Counter[str] = Counter()
    species_environment_counts: Counter[str] = Counter()

    for image_path in iter_source_images(collection):
        metadata = parse_source_metadata(image_path, strain_species_mapping)
        species_counts[metadata.species] += 1
        strain_counts[metadata.strain] += 1
        environment_counts[metadata.environment] += 1
        parse_status_counts[metadata.parse_status] += 1
        species_environment_counts[f"{metadata.species}::{metadata.environment}"] += 1

    return DatasetCollectionSummary(
        collection_key=collection_key,
        display_name=collection.display_name,
        quality_tier=collection.quality_tier,
        source_root=str(collection.path),
        image_count=sum(species_counts.values()),
        species_count=len(species_counts),
        strain_count=len(strain_counts),
        environment_count=len(environment_counts),
        parse_status_counts=dict(parse_status_counts),
        species_image_counts=dict(sorted(species_counts.items())),
        strain_image_counts=dict(sorted(strain_counts.items())),
        environment_image_counts=dict(sorted(environment_counts.items())),
        species_environment_counts=dict(sorted(species_environment_counts.items())),
    )



def build_dataset_eda_report(
    source_collections: list[str] | None = None,
) -> DatasetEdaReport:
    collection_names = resolve_source_collection_names(source_collections)
    summaries = [build_dataset_collection_summary(name) for name in collection_names]

    species: set[str] = set()
    strains: set[str] = set()
    environments: set[str] = set()
    total_images = 0

    for summary in summaries:
        total_images += summary.image_count
        species.update(summary.species_image_counts)
        strains.update(summary.strain_image_counts)
        environments.update(summary.environment_image_counts)

    return DatasetEdaReport(
        collections=summaries,
        total_images=total_images,
        total_species=len(species),
        total_strains=len(strains),
        total_environments=len(environments),
    )



def build_species_environment_matrix(
    report: DatasetEdaReport,
    max_species: int | None = None,
) -> tuple[list[str], list[str], np.ndarray]:
    species_environment_counts: Counter[tuple[str, str]] = Counter()
    for summary in report.collections:
        if summary.quality_tier != "curated":
            continue
        for key, count in summary.species_environment_counts.items():
            species_name, environment_name = key.split("::", 1)
            if species_name == "unknown" or environment_name == "unknown":
                continue
            species_environment_counts[(species_name, environment_name)] += count

    environments = sorted({environment for _, environment in species_environment_counts})
    species_names = sorted(
        {species_name for species_name, _ in species_environment_counts},
        key=lambda name: -sum(species_environment_counts[(name, env)] for env in environments),
    )
    if max_species is not None:
        species_names = species_names[:max_species]

    matrix = np.zeros((len(species_names), len(environments)))
    for row_index, species_name in enumerate(species_names):
        for column_index, environment_name in enumerate(environments):
            matrix[row_index, column_index] = species_environment_counts.get((species_name, environment_name), 0)
    return species_names, environments, matrix


def render_species_environment_heatmap(
    species_names: list[str],
    environments: list[str],
    matrix: np.ndarray,
    output_path: Path,
    *,
    title: str = "Species x Media Distribution (CYA variants normalized)",
    style: HeatmapStyle | None = None,
) -> Path:
    active_style = style or HeatmapStyle()
    figure, axis = plt.subplots(figsize=active_style.figure_size)
    image = axis.imshow(matrix, cmap="YlOrRd", aspect="auto")
    figure.canvas.draw()
    axis.set_xticks(range(len(environments)))
    axis.set_xticklabels(environments, fontsize=active_style.tick_label_size, rotation=0)
    axis.set_yticks(range(len(species_names)))
    axis.set_yticklabels([
        species_name.replace("Penicillium ", "P. ")[:24] for species_name in species_names
    ], fontsize=active_style.tick_label_size)
    axis.set_xlabel("Growth medium", fontsize=active_style.axis_label_size)
    axis.set_ylabel("Species", fontsize=active_style.axis_label_size)
    axis.set_title(title, fontsize=active_style.title_size)
    matrix_max = float(matrix.max()) if matrix.size else 0.0
    axis_bbox = axis.get_window_extent(renderer=figure.canvas.get_renderer())
    cell_height_pixels = axis_bbox.height / max(len(species_names), 1)
    annotation_font_size = max(active_style.annotation_size, int(cell_height_pixels * 0.8 * 72 / figure.dpi))
    for row_index in range(len(species_names)):
        for column_index in range(len(environments)):
            value = matrix[row_index, column_index]
            if value > 0:
                axis.text(
                    column_index,
                    row_index,
                    str(int(value)),
                    ha="center",
                    va="center",
                    fontsize=annotation_font_size,
                    fontweight="bold",
                    color="white" if matrix_max and value > matrix_max / 2 else "black",
                )
    colorbar = plt.colorbar(image, ax=axis)
    colorbar.ax.tick_params(labelsize=active_style.colorbar_tick_size)
    colorbar.set_label("Images", fontsize=active_style.colorbar_label_size)
    figure.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)
    return output_path


def render_text_report(report: DatasetEdaReport) -> str:
    lines = [
        f"total_images: {report.total_images}",
        f"total_species: {report.total_species}",
        f"total_strains: {report.total_strains}",
        f"total_environments: {report.total_environments}",
    ]
    for summary in report.collections:
        lines.extend(
            [
                "",
                f"[{summary.collection_key}] {summary.display_name}",
                f"quality_tier: {summary.quality_tier}",
                f"source_root: {summary.source_root}",
                f"image_count: {summary.image_count}",
                f"species_count: {summary.species_count}",
                f"strain_count: {summary.strain_count}",
                f"environment_count: {summary.environment_count}",
                f"parse_status_counts: {json.dumps(summary.parse_status_counts, sort_keys=True)}",
                f"species_image_counts: {json.dumps(summary.species_image_counts, sort_keys=True)}",
                f"environment_image_counts: {json.dumps(summary.environment_image_counts, sort_keys=True)}",
            ]
        )
    return "\n".join(lines)



def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze canonical source dataset collections")
    parser.add_argument(
        "--source-collection",
        action="append",
        default=[],
        dest="source_collections",
        help=f"Collection key to analyze (repeatable: {', '.join(SOURCE_COLLECTIONS)})",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path for report output",
    )
    args = parser.parse_args()

    report = build_dataset_eda_report(args.source_collections)
    payload = asdict(report)
    output = (
        json.dumps(payload, indent=2, sort_keys=True)
        if args.format == "json"
        else render_text_report(report)
    )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n")
    else:
        print(output)


if __name__ == "__main__":
    main()
