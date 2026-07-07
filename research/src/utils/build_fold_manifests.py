from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import (
    DATASET_ROOT,
    PREPARED_SEGMENTS_METADATA_PATH,
    STRAIN_SPECIES_MAPPING_PATH,
)
from src.lib.cross_validation import N_FOLDS, generate_cv_folds


def _load_segment_rows(segments_metadata_path: Path) -> list[dict[str, Any]]:
    if not segments_metadata_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    payload = json.loads(segments_metadata_path.read_text())
    for item in payload:
        data = item.get("data", item)
        strain = data.get("strain") or item.get("strain")
        species = (
            data.get("specy")
            or data.get("species")
            or item.get("specy")
            or item.get("species")
        )
        environment = data.get("environment") or item.get("environment") or "unknown"
        image_id = item.get("id") or item.get("image_id")
        segment_path = item.get("segment_path") or data.get("segment_path")
        parent_id = (
            item.get("parent_id") or data.get("parent_id") or item.get("parent_item_id")
        )
        if not strain or not species or not image_id:
            continue
        rows.append(
            {
                "image_id": image_id,
                "strain": strain,
                "species": species,
                "environment": environment,
                "segment_path": segment_path,
                "parent_id": parent_id,
            }
        )
    return rows


def build_fold_manifest_rows(
    source_csv: Path = STRAIN_SPECIES_MAPPING_PATH,
    segments_metadata_path: Path = PREPARED_SEGMENTS_METADATA_PATH,
    n_folds: int = N_FOLDS,
) -> list[dict[str, Any]]:
    if not source_csv.exists():
        raise FileNotFoundError(f"Source mapping CSV not found at {source_csv}")

    mapping_df = pd.read_csv(source_csv)
    if "Strain" not in mapping_df.columns or "Species" not in mapping_df.columns:
        raise ValueError(
            "Source mapping CSV must contain 'Strain' and 'Species' columns."
        )

    folds = generate_cv_folds(csv_path=source_csv, n_folds=n_folds)
    segment_rows = _load_segment_rows(segments_metadata_path)

    by_strain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in segment_rows:
        by_strain[row["strain"]].append(row)

    manifest_rows: list[dict[str, Any]] = []
    for fold_idx, fold_selection in enumerate(folds):
        held_out_strains = set(fold_selection.values())
        training_df = mapping_df[~mapping_df["Strain"].isin(held_out_strains)]

        for species, test_strain in sorted(fold_selection.items()):
            query_rows = by_strain.get(test_strain, [])
            media_values = sorted({row["environment"] for row in query_rows})
            manifest_rows.append(
                {
                    "fold": fold_idx,
                    "species": species,
                    "test_strain": test_strain,
                    "train_strains": sorted(training_df["Strain"].tolist()),
                    "train_species": sorted(training_df["Species"].unique().tolist()),
                    "query_image_ids": sorted(row["image_id"] for row in query_rows),
                    "query_media": media_values,
                    "query_count": len(query_rows),
                }
            )

    return manifest_rows


def write_fold_manifests(
    output_dir: Path = DATASET_ROOT / "folds",
    source_csv: Path = STRAIN_SPECIES_MAPPING_PATH,
    segments_metadata_path: Path = PREPARED_SEGMENTS_METADATA_PATH,
    n_folds: int = N_FOLDS,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_fold_manifest_rows(
        source_csv=source_csv,
        segments_metadata_path=segments_metadata_path,
        n_folds=n_folds,
    )

    written: list[Path] = []
    for row in rows:
        target = (
            output_dir
            / f"fold_{row['fold']}_{row['test_strain'].replace(' ', '_')}.json"
        )
        target.write_text(json.dumps(row, indent=2))
        written.append(target)

    summary_rows = [
        {
            "fold": row["fold"],
            "species": row["species"],
            "test_strain": row["test_strain"],
            "query_count": row["query_count"],
            "query_media": ",".join(row["query_media"]),
            "train_strain_count": len(row["train_strains"]),
            "train_species_count": len(row["train_species"]),
        }
        for row in rows
    ]
    pd.DataFrame(summary_rows).to_csv(
        output_dir / "fold_manifest_summary.csv", index=False
    )
    return written


def main() -> None:
    written = write_fold_manifests()
    print(json.dumps({"written": [str(path) for path in written]}, indent=2))


if __name__ == "__main__":
    main()
