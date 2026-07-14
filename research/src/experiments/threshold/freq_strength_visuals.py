from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from qdrant_client import QdrantClient
from sklearn.metrics import confusion_matrix

from src.analysis.visualization.visualize_prediction import visualize_prediction_by_environment
from src.config import QDRANT_API_KEY, QDRANT_URL, SEGMENTED_IMAGE_DIR
from src.experiments.retrieval.run import aggregate_predictions, load_strain_to_species_mapping
from src.experiments.threshold.full_classes import (
    COLLECTION,
    EXTRACTOR_KEY,
    FEATURES_CACHE,
    GROUPED_SETS_JSON,
    OUTPUT_DIR,
    TOP_N,
    build_grouped_query_sets,
    canonical_species_label,
    extract_feature_cache,
    normalize_qdrant_strain,
)
from src.utils.qdrant_query import build_filter

RESULTS_ROOT = OUTPUT_DIR / "freq_strength"


def _load_grouped_sets() -> list[dict[str, Any]]:
    if GROUPED_SETS_JSON.exists():
        with open(GROUPED_SETS_JSON) as f:
            return json.load(f)
    grouped_sets = build_grouped_query_sets()
    with open(GROUPED_SETS_JSON, "w") as f:
        json.dump(grouped_sets, f)
    return grouped_sets


def _load_feature_cache(grouped_sets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if FEATURES_CACHE.exists():
        with open(FEATURES_CACHE) as f:
            data = json.load(f)
        return {item["image_path_rel"]: item for item in data}
    return extract_feature_cache(grouped_sets)


def _query_mode_neighbors(grouped_sets: list[dict[str, Any]], feature_cache: dict[str, dict[str, Any]], environment_mode: str, collection: str) -> dict[str, list[dict[str, Any]]]:
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=120)
    cache: dict[str, list[dict[str, Any]]] = {}
    for grouped in grouped_sets:
        exclude_strain = normalize_qdrant_strain(grouped["strain"]) if grouped["is_known"] else None
        for seg in grouped["segments"]:
            key = seg["image_path_rel"]
            if key in cache or key not in feature_cache:
                continue
            env = seg["environment"] if environment_mode == "E1" else None
            query_filter = build_filter(environment=env, exclude_strain=exclude_strain)
            response = client.query_points(
                collection_name=collection,
                query=feature_cache[key]["vector"],
                using=EXTRACTOR_KEY,
                query_filter=query_filter,
                limit=11,
                with_payload=True,
            )
            neighbors: list[dict[str, Any]] = []
            for point in response.points:
                payload = point.payload or {}
                neighbors.append(
                    {
                        "image_id": str(payload.get("image_id", "")),
                        "image_path": str(payload.get("segment_path", "")),
                        "specy": str(payload.get("specy") or payload.get("species") or "unknown"),
                        "score": float(point.score),
                        "strain": str(payload.get("strain", "")),
                        "environment": str(payload.get("environment", "")),
                        "angle": str(payload.get("angle", "")),
                        "parent_id": str(payload.get("parent_id") or payload.get("parent_item_id") or ""),
                        "segment_index": int(payload.get("segment_index", -1) or -1),
                    }
                )
            cache[key] = neighbors
    return cache


def _rank_group(grouped: dict[str, Any], neighbor_cache: dict[str, list[dict[str, Any]]], strain_to_specy: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_results: list[dict[str, Any]] = []
    for seg in grouped["segments"]:
        neighbors = neighbor_cache.get(seg["image_path_rel"], [])
        if not neighbors:
            continue
        raw_results.append(
            {
                "query_image_id": seg["image_path_rel"],
                "query_image_path": seg["image_path"],
                "query_parent_id": seg["image_path_rel"],
                "query_environment": seg["environment"],
                "query_angle": seg["angle"],
                "query_segment_index": seg["segment_index"],
                "neighbors": neighbors,
            }
        )
    aggregated = aggregate_predictions(raw_results, strain_to_specy, 11, strategy="freq_strength")
    ranked = [{"specy": species, "score": float(score)} for species, score in aggregated[:TOP_N]]
    return raw_results, ranked


def _write_mode_outputs(grouped_sets: list[dict[str, Any]], environment_mode: str, collection: str) -> Path:
    out_dir = RESULTS_ROOT / environment_mode
    viz_dir = out_dir / "visualizations"
    viz_dir.mkdir(parents=True, exist_ok=True)
    feature_cache = _load_feature_cache(grouped_sets)
    neighbor_cache = _query_mode_neighbors(grouped_sets, feature_cache, environment_mode, collection)
    strain_to_specy = load_strain_to_species_mapping()
    rows: list[dict[str, Any]] = []
    pred_json: list[dict[str, Any]] = []
    for grouped in grouped_sets:
        raw_results, ranked = _rank_group(grouped, neighbor_cache, strain_to_specy)
        if not raw_results or not ranked:
            continue
        predicted = canonical_species_label(ranked[0]["specy"])
        gt = canonical_species_label(grouped["species_label"])
        is_correct = bool(grouped["is_known"] and predicted == gt)
        row: dict[str, Any] = {
            "sample_id": grouped["sample_id"],
            "strain": grouped["strain"],
            "species_label": grouped["species_label"],
            "is_known": grouped["is_known"],
            "environment_mode": environment_mode,
            "predicted_species": ranked[0]["specy"],
            "predicted_confidence": ranked[0]["score"],
            "correct": is_correct,
            "image_path": ";".join(seg["image_path"] for seg in grouped["segments"]),
            "environment": ",".join(sorted({seg["environment"] for seg in grouped["segments"]})),
        }
        for i in range(TOP_N):
            if i < len(ranked):
                row[f"s{i}_species"] = ranked[i]["specy"]
                row[f"s{i}_score"] = ranked[i]["score"]
            else:
                row[f"s{i}_species"] = ""
                row[f"s{i}_score"] = 0.0
        rows.append(row)
        pred = {
            "ground_truth": grouped["species_label"],
            "predicted_specy": ranked[0]["specy"],
            "correct": is_correct,
            "predicted_confidence": ranked[0]["score"],
            "feature_extractor": EXTRACTOR_KEY,
            "strategy": "freq_strength",
            "environment": environment_mode,
            "strain": grouped["strain"],
            "sample_id": grouped["sample_id"],
            "raw_results": raw_results,
            "aggregated_results": ranked,
        }
        pred_json.append(pred)
        visualize_prediction_by_environment(
            prediction_result=pred,
            segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
            output_path=str(viz_dir / f"{grouped['sample_id'].replace('/', '_').replace(':', '__')}.jpg"),
            k=7,
        )
    csv_path = out_dir / "retrieval_results.csv"
    with open(csv_path, "w", newline="") as f:
        fieldnames = list(rows[0].keys()) if rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    with open(out_dir / "prediction_results.json", "w") as f:
        json.dump(pred_json, f, indent=2)
    _draw_confusion(rows, out_dir / "confusion_matrix.png", title=f"freq_strength {environment_mode}")
    return csv_path


def _draw_confusion(rows: list[dict[str, Any]], output_path: Path, title: str) -> None:
    y_true = [canonical_species_label(row["species_label"]) if int(row["is_known"]) == 1 else "UNKNOWN" for row in rows]
    y_pred = [canonical_species_label(row["predicted_species"]) for row in rows]
    labels = sorted({*y_true, *y_pred} - {"UNKNOWN"}) + ["UNKNOWN"]
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)
    fig, ax = plt.subplots(figsize=(max(12, len(labels) * 0.45), max(10, len(labels) * 0.4)))
    sns.heatmap(cm_df, annot=True, fmt="d", cmap="YlOrRd", linewidths=0.5, linecolor="white", ax=ax, annot_kws={"fontsize": 6})
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(title)
    plt.xticks(rotation=90, fontsize=6)
    plt.yticks(rotation=0, fontsize=6)
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def run(collection: str = COLLECTION) -> dict[str, str]:
    grouped_sets = _load_grouped_sets()
    outputs = {}
    for mode in ("E1", "E2"):
        outputs[mode] = str(_write_mode_outputs(grouped_sets, mode, collection))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Grouped query freq_strength E1/E2 visualizations")
    parser.add_argument("--collection", default=COLLECTION)
    args = parser.parse_args()
    print(json.dumps(run(collection=args.collection), indent=2))


if __name__ == "__main__":
    main()
