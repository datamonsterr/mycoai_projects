"""Unified evaluation module.

This file is the canonical path for prediction and species evaluation logic.
It consolidates functionality previously split across classification modules.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.config import (
    DATASET_ROOT,
    RESULTS_DIR,
    SEGMENTED_IMAGE_DIR,
    STRAIN_SPECIES_MAPPING_PATH,
)
from src.experiments.feature_extraction.feature_extractors import FeatureExtractor
from src.utils.qdrant_query import find_nearest_neighbors_by_id, find_nearest_neighbors_by_image


OLD_ENV_LABELS = {
    None: "E1",
    "all": "E2",
}


def normalize_environment_label(environment: Optional[str]) -> str:
    if environment in OLD_ENV_LABELS:
        return OLD_ENV_LABELS[environment]
    if isinstance(environment, str) and environment.startswith(("E3_", "E4_")):
        return environment
    if isinstance(environment, str):
        return f"E3_{environment}"
    return "E1"


def normalize_segmentation_label(collection_name: str, identifier: str = "") -> str:
    source = f"{collection_name} {identifier}".lower()
    if "kmeans" in source:
        return "kmeans"
    if "yolo" in source:
        return "yolo"
    return "yolo"


def summarize_rank_scores(aggregated_results: Sequence[Dict[str, Any]], top_n: int = 5) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for index in range(top_n):
        entry = aggregated_results[index] if index < len(aggregated_results) else None
        summary[f"s{index}_species"] = entry.get("specy", "unknown") if entry else "unknown"
        summary[f"s{index}_score"] = float(entry.get("score", 0.0)) if entry else 0.0
    return summary


def get_extractor_by_name(name: str) -> Optional[FeatureExtractor]:
    """Build a feature extractor instance from a normalized short name."""
    from src.experiments.feature_extraction.feature_extractors import (
        ColorHistogramExtractor,
        ColorHistogramHSExtractor,
        EfficientNetB1Extractor,
        EfficientNetB1FinetunedExtractor,
        GaborExtractor,
        HOGExtractor,
        MobileNetV2Extractor,
        MobileNetV2FinetunedExtractor,
        ResNet50Extractor,
        ResNet50FinetunedExtractor,
    )

    normalized = name.lower()
    if normalized == "resnet50":
        return ResNet50Extractor()
    if normalized == "resnet50_finetuned":
        return ResNet50FinetunedExtractor()
    if normalized == "mobilenetv2":
        return MobileNetV2Extractor()
    if normalized == "mobilenetv2_finetuned":
        return MobileNetV2FinetunedExtractor()
    if normalized in {"efficientnetv2", "efficientnetb1"}:
        return EfficientNetB1Extractor()
    if normalized == "efficientnetb1_finetuned":
        return EfficientNetB1FinetunedExtractor()
    if normalized == "hog":
        return HOGExtractor()
    if normalized == "gabor":
        return GaborExtractor()
    if normalized == "colorhistogram":
        return ColorHistogramExtractor()
    if normalized == "colorhistogramhs":
        return ColorHistogramHSExtractor()
    return None


def load_strain_to_species_mapping(
    csv_path: str = str(STRAIN_SPECIES_MAPPING_PATH),
) -> Dict[str, str]:
    """Load a ``strain -> species`` mapping from CSV."""
    strain_to_specy: Dict[str, str] = {}
    with open(csv_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            strain_to_specy[row["Strain"]] = row["Species"]
    return strain_to_specy


def get_all_images_for_strain(
    client: QdrantClient,
    collection_name: str,
    strain: str,
    environment: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch all points for one strain (optionally filtered by environment)."""
    conditions: list[FieldCondition | Filter] = [
        FieldCondition(key="strain", match=MatchValue(value=strain))
    ]

    if environment and environment.lower() != "all":
        conditions.append(
            FieldCondition(key="environment", match=MatchValue(value=environment))
        )

    search_filter = Filter(must=list(conditions))

    all_images: List[Dict[str, Any]] = []
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            scroll_filter=search_filter,
            limit=100,
            offset=offset,
            with_payload=True,
        )

        for point in points:
            payload = point.payload or {}
            all_images.append(
                {
                    "image_id": payload.get("image_id"),
                    "strain": payload.get("strain"),
                    "environment": payload.get("environment"),
                    "angle": payload.get("angle"),
                    "specy": payload.get("specy") or payload.get("species"),
                    "parent_id": payload.get("parent_id") or payload.get("parent_item_id"),
                    "segment_index": payload.get("segment_index"),
                    "bbox": payload.get("bbox"),
                    "image_path": payload.get("segment_path"),
                }
            )

        if next_offset is None:
            break
        offset = next_offset

    return all_images


def load_prepared_segments_metadata(
    metadata_path: Path = DATASET_ROOT / "prepared_segments_metadata.json",
) -> Dict[str, Dict[str, Any]]:
    if not metadata_path.exists():
        return {}
    payload = json.loads(metadata_path.read_text())
    return {row["id"]: row for row in payload if row.get("id")}


def load_fold_manifest(
    fold: int,
    strain: str,
    folds_dir: Path = DATASET_ROOT / "folds",
) -> Dict[str, Any]:
    target = folds_dir / f"fold_{fold}_{strain.replace(' ', '_')}.json"
    if not target.exists():
        raise FileNotFoundError(f"Fold manifest not found: {target}")
    return json.loads(target.read_text())


def build_query_group_from_manifest(
    segment_ids: Sequence[str],
    prepared_segments: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    query_group: List[Dict[str, Any]] = []
    for segment_id in segment_ids:
        row = prepared_segments.get(segment_id)
        if not row:
            continue
        data = row.get("data", {})
        segment_path = row.get("segment_path") or data.get("segment_path")
        query_group.append(
            {
                "image_id": segment_id,
                "image_path": str(DATASET_ROOT.parent / segment_path)
                if isinstance(segment_path, str)
                else None,
                "parent_id": row.get("parent_id") or data.get("parent_id"),
                "environment": data.get("environment", "unknown"),
                "angle": data.get("angle", "unknown"),
                "segment_index": row.get("index", data.get("segment_index", 0)),
            }
        )
    return query_group


def collect_testsets_from_images(
    strain_images: Sequence[Dict[str, Any]],
    exclude_env: Optional[str] = None,
) -> List[List[Dict[str, Any]]]:
    env_segment_angle_images: Dict[str, Dict[Any, Dict[Any, List[Dict[str, Any]]]]] = (
        defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for img in strain_images:
        env = img.get("environment", "unknown")
        if exclude_env is not None and env == exclude_env:
            continue
        segment_idx = img.get("segment_index", 0)
        image_id = img.get("image_id", "")
        seg_match = re.search(r"segment_(\d+)", image_id)
        if seg_match:
            segment_idx = int(seg_match.group(1)) - 1
        angle = img.get("angle", "unknown")
        env_segment_angle_images[env][segment_idx][angle].append(img)

    test_sets: List[List[Dict[str, Any]]] = []
    test_configs = [
        (0, "ob"),
        (0, "rev"),
        (1, "ob"),
        (1, "rev"),
        (2, "ob"),
        (2, "rev"),
    ]

    for segment_idx, preferred_angle in test_configs:
        skip_config = False
        test_set: List[Dict[str, Any]] = []
        for env in sorted(env_segment_angle_images.keys()):
            segment_images = env_segment_angle_images[env]
            img_selected: Optional[Dict[str, Any]] = None

            if segment_idx in segment_images:
                angle_variations = {
                    "ob": ["ob", "obverse"],
                    "rev": ["rev", "reverse"],
                }
                for angle_var in angle_variations.get(preferred_angle, [preferred_angle]):
                    candidates = segment_images[segment_idx].get(angle_var, [])
                    if candidates:
                        img_selected = candidates[0]
                        break

                if img_selected is None:
                    for angle in sorted(segment_images[segment_idx].keys()):
                        candidates = segment_images[segment_idx][angle]
                        if candidates:
                            img_selected = candidates[0]
                            break

            if img_selected is None:
                skip_config = True
                break

            test_set.append(img_selected)

        if not skip_config and test_set and len(test_set) == len(env_segment_angle_images):
            test_sets.append(test_set)

    available_segments = sorted(env_segment_angle_images[env].keys()) if env_segment_angle_images else []
    print(f"  [collect] available_segments={available_segments}, built_test_sets={len(test_sets)}")
    return test_sets


def filter_siblings(
    neighbors: List[Dict[str, Any]], query_parent_id: Optional[str]
) -> List[Dict[str, Any]]:
    """Remove neighbors from the same parent image as the query segment."""
    if query_parent_id is None:
        return neighbors
    return [n for n in neighbors if n.get("parent_id") != query_parent_id]


def aggregate_predictions(
    all_results: List[Dict[str, Any]],
    strain_to_specy: Dict[str, str],
    k: int,
    min_samples: Optional[int] = None,
    strategy: str = "weighted",
) -> List[Tuple[str, float]]:
    """Aggregate per-segment neighbors into strain-level species ranking.

    Strategies
    ----------
    weighted (default)
        ``scores[X] / total_known_neighbors`` — fraction of total neighbor
        score-mass belonging to species X.  Susceptible to dilution when
        similar species split the neighbor pool (values rarely exceed 0.5).

    uni
        ``count[X] / total_known_neighbors`` — fraction of neighbor *counts*
        belonging to species X (ignore similarity magnitudes).

    relative
        ``scores[X] / Σ scores[all]`` — each species gets its share of
        the *total* raw-evidence sum.  Top species → 1.0 when it dominates;
        all scores naturally sum to 1.  **Recommended** when you need the
        ranking score to reflect confidence relative to alternatives.

    per_species_avg
        ``scores[X] / count[X]`` — mean cosine similarity for species X
        (natural 0‑1 range).  High-confidence single-hit species can reach
        scores near 1.0, but a single outlier neighbor can inflate the
        score of a rare species.

    max_score
        ``max(neighbor.score for neighbor of species X)`` — single best
        match (natural 0‑1).  Ignores prevalence across the neighbor set.

    perquery_avg
        Per query image: ``sum_scores_for_X_in_query / K``, then
        arithmetic mean across all query images.  Equivalent to *weighted*
        when every neighbor maps to a known species, but differs when
        unknown neighbors are present (this strategy always divides by K,
        not by the count of known neighbors).

    perquery_norm_avg
        For each query image, normalize intra-query per-species scores so
        they sum to 1 (soft allocation), then compute the arithmetic mean
        across query images.  Treats every query as an equal "voter".
        Natural 0‑1 range.

    freq_strength
        Independent per-species score (does NOT sum to 1 across species).
        ``(queries_with_X / M) * (scores[X] / count[X])`` — how often the
        species appears across query images, multiplied by its average
        match strength.  Both factors are in [0, 1], product is in [0, 1].
        Favours species that appear consistently AND match strongly.
    """
    del min_samples

    species_scores: Counter[str] = Counter()
    species_counts: Counter[str] = Counter()
    queries_with_species: Dict[str, set] = {}

    for qi, result in enumerate(all_results):
        neighbors = result["neighbors"]
        for neighbor in neighbors:
            specy = neighbor.get("specy")
            score = neighbor.get("score", 0.0)

            if not specy or specy == "unknown":
                strain = neighbor.get("strain")
                if strain:
                    specy = strain_to_specy.get(strain, "unknown")

            if specy and specy != "unknown":
                species_scores[specy] += score
                species_counts[specy] += 1
                if specy not in queries_with_species:
                    queries_with_species[specy] = set()
                queries_with_species[specy].add(qi)

    aggregated: List[Tuple[str, float]] = []
    total_neighbors = sum(species_counts.values())
    total_scores = sum(species_scores.values())

    # ── per-query helpers ──────────────────────────────────────────
    per_query_species: Dict[int, Dict[str, float]] = {}
    per_query_total: Dict[int, float] = {}
    for qi, result in enumerate(all_results):
        qmap: Dict[str, float] = {}
        for neighbor in result["neighbors"]:
            specy = neighbor.get("specy")
            score = neighbor.get("score", 0.0)
            if not specy or specy == "unknown":
                strain = neighbor.get("strain")
                if strain:
                    specy = strain_to_specy.get(strain, "unknown")
            if specy and specy != "unknown":
                qmap[specy] = qmap.get(specy, 0.0) + score
        per_query_species[qi] = qmap
        qt = sum(qmap.values())
        per_query_total[qi] = qt if qt > 0 else 1.0

    num_queries = len(all_results)

    for specy, total_score in species_scores.items():
        count = species_counts.get(specy, 0)

        if strategy == "weighted":
            final_score = total_score / total_neighbors if total_neighbors > 0 else 0.0

        elif strategy == "uni":
            final_score = count / total_neighbors if total_neighbors > 0 else 0.0

        elif strategy == "relative":
            final_score = total_score / total_scores if total_scores > 0 else 0.0

        elif strategy == "per_species_avg":
            final_score = total_score / count if count > 0 else 0.0

        elif strategy == "max_score":
            best = 0.0
            for result in all_results:
                for neighbor in result["neighbors"]:
                    nb_specy = neighbor.get("specy")
                    if not nb_specy or nb_specy == "unknown":
                        nb_strain = neighbor.get("strain")
                        if nb_strain:
                            nb_specy = strain_to_specy.get(nb_strain, "unknown")
                    if nb_specy == specy:
                        best = max(best, neighbor.get("score", 0.0))
            final_score = best

        elif strategy == "perquery_avg":
            accum = 0.0
            for qi in range(num_queries):
                qs = per_query_species[qi].get(specy, 0.0)
                accum += qs / k
            final_score = accum / num_queries if num_queries > 0 else 0.0

        elif strategy == "freq_strength":
            freq = len(queries_with_species.get(specy, set())) / num_queries if num_queries > 0 else 0.0
            strength = total_score / count if count > 0 else 0.0
            final_score = freq * strength

        elif strategy == "perquery_norm_avg":
            accum = 0.0
            for qi in range(num_queries):
                qs = per_query_species[qi].get(specy, 0.0)
                accum += qs / per_query_total[qi]
            final_score = accum / num_queries if num_queries > 0 else 0.0

        else:
            final_score = float(total_score)

        aggregated.append((specy, final_score))

    aggregated.sort(key=lambda x: x[1], reverse=True)
    return aggregated


def find_neighbors(
    client: QdrantClient,
    collection_name: str,
    query_image_id: str,
    feature_extractor: FeatureExtractor,
    k: int = 10,
    environment: Optional[str] = None,
    exclude_self: bool = True,
    exclude_environment: Optional[str] = None,
    exclude_strain: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compatibility helper to query neighbors for one image ID."""
    return find_nearest_neighbors_by_id(
        client=client,
        collection_name=collection_name,
        query_image_id=query_image_id,
        feature_type=feature_extractor.name,
        num_neighbors=k,
        environment=environment,
        exclude_self=exclude_self,
        exclude_environment=exclude_environment,
        exclude_strain=exclude_strain,
    )


def predict(
    client: QdrantClient,
    collection_name: str,
    strain: str,
    feature_extractor: FeatureExtractor,
    k: int = 5,
    min_samples: Optional[int] = None,
    without_siblings: bool = True,
    environment: Optional[str] = None,
    strategy: str = "weighted",
    strain_to_specy_path: str = str(STRAIN_SPECIES_MAPPING_PATH),
    segmented_image_dir: str = str(SEGMENTED_IMAGE_DIR),
    output_dir: str = str(RESULTS_DIR),
) -> Dict[str, Any]:
    """Predict species for one strain by aggregating over its segments."""
    del segmented_image_dir
    del output_dir

    strain_to_specy = load_strain_to_species_mapping(strain_to_specy_path)
    ground_truth_specy = strain_to_specy.get(strain, "unknown")

    query_images = get_all_images_for_strain(
        client=client,
        collection_name=collection_name,
        strain=strain,
        environment=environment,
    )

    if not query_images:
        return {
            "strain": strain,
            "ground_truth": ground_truth_specy,
            "predicted_specy": "unknown",
            "correct": False,
            "predicted_confidence": 0.0,
            "error": "No images found",
        }

    raw_results: List[Dict[str, Any]] = []

    for query_img in query_images:
        image_id = query_img["image_id"]
        parent_id = query_img["parent_id"]

        neighbors = find_nearest_neighbors_by_id(
            client=client,
            collection_name=collection_name,
            query_image_id=image_id,
            feature_type=feature_extractor.name,
            num_neighbors=k * 10,
            environment=(
                environment if environment and environment.lower() != "all" else None
            ),
            exclude_self=True,
            exclude_strain=strain,
        )

        if without_siblings:
            neighbors = filter_siblings(neighbors, parent_id)

        neighbors = neighbors[:k]

        raw_results.append(
            {
                "query_image_id": image_id,
                "query_environment": query_img.get("environment"),
                "neighbors": neighbors,
            }
        )

    aggregated = aggregate_predictions(
        raw_results,
        strain_to_specy,
        k,
        min_samples,
        strategy,
    )

    if not aggregated:
        predicted_specy = "unknown"
        confidence = 0.0
    else:
        predicted_specy = aggregated[0][0]
        confidence = aggregated[0][1]

    is_correct = predicted_specy == ground_truth_specy
    aggregated_results = [{"specy": s, "score": sc} for s, sc in aggregated]
    score_summary = summarize_rank_scores(aggregated_results)

    return {
        "strain": strain,
        "ground_truth": ground_truth_specy,
        "predicted_specy": predicted_specy,
        "correct": is_correct,
        "predicted_confidence": confidence,
        "aggregated_results": aggregated_results,
        "raw_results": raw_results,
        "feature_extractor": feature_extractor.name,
        "strategy": strategy,
        "environment": environment,
        **score_summary,
    }


def draw_confusion_matrix(
    predictions: List[Dict[str, Any]],
    output_path: str = str(RESULTS_DIR / "confusion_matrix.png"),
    figsize: Tuple[int, int] = (12, 10),
) -> None:
    """Render and save confusion matrix for species predictions."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    y_true = [p["ground_truth"] for p in predictions]
    y_pred = [p["predicted_specy"] for p in predictions]

    correct_count = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = (correct_count / len(predictions) * 100.0) if predictions else 0.0

    labels = sorted(set(y_true))
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    plt.figure(figsize=figsize)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="Blues",
    )
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(
        f"Confusion Matrix - Accuracy: {accuracy:.2f}% ({correct_count}/{len(predictions)})"
    )
    plt.xticks(rotation=90)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def print_selection_report(selected: Dict[str, str], output_dir: str) -> str:
    """Write selected strain-per-species report."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"strain_selection_report_{timestamp}.txt")
    with open(report_path, "w") as f:
        f.write(f"Total species: {len(selected)}\\n")
        for species, strain in selected.items():
            f.write(f"{species}: {strain}\\n")
    return report_path


def print_prediction_results(
    results: List[Dict[str, Any]],
    output_dir: str,
    collection_name: Optional[str] = None,
    k: Optional[int] = None,
    media: Optional[str] = None,
    strategy: Optional[str] = None,
) -> str:
    """Write human-readable and JSON prediction summaries."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(output_dir, f"prediction_report_{timestamp}.txt")

    correct_count = sum(1 for r in results if r["correct"])
    accuracy = correct_count / len(results) if results else 0.0
    media_label = normalize_environment_label(media)

    with open(report_path, "w") as f:
        f.write(f"Accuracy: {accuracy:.4f}\\n")
        for r in results:
            f.write(
                f"{r['strain']} ({r['ground_truth']}) -> {r['predicted_specy']} "
                f"[{'Correct' if r['correct'] else 'Wrong'}]\\n"
            )

    json_path = os.path.join(output_dir, "evaluation_results.json")
    summary = {
        "overall_accuracy": accuracy,
        "correct_predictions": correct_count,
        "total_strains": len(results),
        "timestamp": timestamp,
        "collection": collection_name,
        "k": k,
        "media_strategy": media_label,
        "aggregation_strategy": strategy,
        "results": results,
    }
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    analytics_path = os.path.join(output_dir, "analytics_summary.json")
    per_species = Counter((r["ground_truth"], r["predicted_specy"]) for r in results)
    analytics = {
        "overall_accuracy": accuracy,
        "correct_predictions": correct_count,
        "total_predictions": len(results),
        "per_pair_counts": [
            {"ground_truth": gt, "predicted_species": pred, "count": count}
            for (gt, pred), count in sorted(per_species.items())
        ],
    }
    with open(analytics_path, "w") as f:
        json.dump(analytics, f, indent=2)

    return report_path


def write_evaluation_csv(
    results: List[Dict[str, Any]],
    output_dir: str,
    feature_extractor: FeatureExtractor,
    media: Optional[str],
    strategy: str,
    collection_name: Optional[str] = None,
    k: Optional[int] = None,
) -> Optional[str]:
    """Write ranked species predictions to CSV."""
    if not results:
        return None

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if media is None:
        media_label = "same"
    elif isinstance(media, str) and media.lower() == "all":
        media_label = "all"
    else:
        media_label = str(media)

    agg_label = "weighted" if strategy == "weighted" else strategy

    max_rank = max(len(r.get("aggregated_results", [])) for r in results)

    base_fields = [
        "strain",
        "test_set_index",
        "ground_truth",
        "feature_extractor",
        "media",
        "aggregation",
        "collection",
        "k",
        "predicted_species",
        "predicted_confidence",
    ]

    rank_fields: List[str] = []
    for rank in range(1, max_rank + 1):
        rank_fields.append(f"rank{rank}_species")
        rank_fields.append(f"rank{rank}_score")

    fieldnames = base_fields + rank_fields
    csv_name = f"{output_path.name}.csv"
    csv_path = output_path / csv_name

    with open(csv_path, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for result in results:
            row: Dict[str, Any] = {
                "strain": result.get("strain"),
                "test_set_index": result.get("test_set_index"),
                "ground_truth": result.get("ground_truth"),
                "feature_extractor": feature_extractor.name,
                "media": media_label,
                "aggregation": agg_label,
                "collection": collection_name or "",
                "k": k if k is not None else "",
                "predicted_species": result.get("predicted_specy", "unknown"),
                "predicted_confidence": result.get("predicted_confidence", 0.0),
            }

            aggregated = result.get("aggregated_results", [])
            for idx, entry in enumerate(aggregated, start=1):
                row[f"rank{idx}_species"] = entry.get("specy")
                row[f"rank{idx}_score"] = entry.get("score")

            writer.writerow(row)

    return str(csv_path)


def collect_testset(
    client: QdrantClient,
    collection_name: str,
    strain: str,
    environment_strategy: str,
) -> List[List[Dict[str, Any]]]:
    """Build per-strain test sets according to E1/E2/E3/E4 strategy."""
    if environment_strategy.startswith("E3_"):
        is_e3 = True
        is_e4 = False
        target_env = environment_strategy[3:]
        exclude_env = None
        strain_images = get_all_images_for_strain(
            client=client,
            collection_name=collection_name,
            strain=strain,
            environment=target_env,
        )
    elif environment_strategy.startswith("E4_"):
        is_e3 = False
        is_e4 = True
        target_env = None
        exclude_env = environment_strategy[3:]
        strain_images = get_all_images_for_strain(
            client=client,
            collection_name=collection_name,
            strain=strain,
            environment=None,
        )
    else:
        is_e3 = False
        is_e4 = False
        target_env = None
        exclude_env = None
        strain_images = get_all_images_for_strain(
            client=client,
            collection_name=collection_name,
            strain=strain,
            environment=None,
        )

    del target_env

    if not strain_images:
        return []

    if is_e3:
        test_sets: List[List[Dict[str, Any]]] = []
        for img in strain_images[:6]:
            test_sets.append([img])
        return test_sets

    return collect_testsets_from_images(
        strain_images,
        exclude_env=exclude_env if is_e4 else None,
    )


def predict_segment_group(
    client: QdrantClient,
    collection_name: str,
    test_group: List[Dict[str, Any]],
    strain: str,
    feature_extractor: FeatureExtractor,
    k: int = 5,
    min_samples: Optional[int] = None,
    without_siblings: bool = True,
    environment: Optional[str] = None,
    strategy: str = "weighted",
    strain_to_specy_path: str = str(STRAIN_SPECIES_MAPPING_PATH),
) -> Dict[str, Any]:
    """Predict species from a provided segment group (one strain test split)."""
    df = pd.read_csv(strain_to_specy_path)
    strain_to_specy = dict(zip(df["Strain"], df["Species"]))
    ground_truth_specy = strain_to_specy.get(strain, "unknown")

    raw_results: List[Dict[str, Any]] = []
    for query_img in test_group:
        image_id = query_img["image_id"]
        image_path = query_img.get("image_path")
        if image_path and not Path(str(image_path)).is_absolute():
            image_path = str(DATASET_ROOT.parent / str(image_path))
        parent_id = query_img["parent_id"]
        img_environment = query_img.get("environment", "unknown")

        search_environment = None
        exclude_environment = None

        if environment is None:
            search_environment = img_environment
        elif environment.lower() == "all":
            search_environment = None
        elif environment.startswith("E4_"):
            exclude_environment = environment[3:]
            search_environment = None
        elif environment.startswith("E3_"):
            search_environment = environment[3:]
        else:
            search_environment = environment

        if image_path:
            neighbors = find_nearest_neighbors_by_image(
                client=client,
                collection_name=collection_name,
                image_path=image_path,
                extractor=feature_extractor,
                feature_type=feature_extractor.name,
                num_neighbors=k * 10,
                environment=search_environment,
                exclude_environment=exclude_environment,
                exclude_strain=strain,
            )
        else:
            neighbors = find_nearest_neighbors_by_id(
                client=client,
                collection_name=collection_name,
                query_image_id=image_id,
                feature_type=feature_extractor.name,
                num_neighbors=k * 10,
                environment=search_environment,
                exclude_self=True,
                exclude_environment=exclude_environment,
                exclude_strain=strain,
            )

        if without_siblings:
            neighbors = filter_siblings(neighbors, parent_id)

        neighbors = neighbors[:k]

        raw_results.append(
            {
                "query_image_id": image_id,
                "query_image_path": image_path,
                "query_environment": img_environment,
                "neighbors": neighbors,
            }
        )

    aggregated = aggregate_predictions(
        raw_results,
        strain_to_specy,
        k,
        min_samples,
        strategy,
    )

    if not aggregated:
        predicted_specy = "unknown"
        confidence = 0.0
    else:
        predicted_specy = aggregated[0][0]
        confidence = aggregated[0][1]

    is_correct = predicted_specy == ground_truth_specy
    aggregated_results = [{"specy": s, "score": sc} for s, sc in aggregated]
    score_summary = summarize_rank_scores(aggregated_results)

    return {
        "strain": strain,
        "ground_truth": ground_truth_specy,
        "predicted_specy": predicted_specy,
        "correct": is_correct,
        "predicted_confidence": confidence,
        "aggregated_results": aggregated_results,
        "raw_results": raw_results,
        "feature_extractor": feature_extractor.name,
        "strategy": strategy,
        "environment": environment,
        **score_summary,
    }


def run_species_evaluation(
    client: QdrantClient,
    collection_name: str,
    feature_extractor: FeatureExtractor,
    k: int = 5,
    min_samples: Optional[int] = None,
    without_siblings: bool = True,
    environment: Optional[str] = None,
    strategy: str = "weighted",
    output_dir: str = str(RESULTS_DIR),
    generate_visualizations: bool = False,
    selected_strains: Optional[Dict[str, str]] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """Run evaluation over selected test strains and return predictions + report path."""
    import pandas as pd

    from src.analysis.visualization.visualize_prediction import (
        batch_visualize_predictions,
    )

    if selected_strains is None:
        if not STRAIN_SPECIES_MAPPING_PATH.exists():
            print(
                f"Error: {STRAIN_SPECIES_MAPPING_PATH} not found. "
                "Please run 'uv run python -m src.utils.generate_strain_mapping' first."
            )
            return [], ""

        df_mapping = pd.read_csv(STRAIN_SPECIES_MAPPING_PATH)
        if "Test" not in df_mapping.columns:
            print(
                "Error: 'Test' column not found in mapping CSV. Please regenerate mapping."
            )
            return [], ""

        test_df = df_mapping[df_mapping["Test"]]
        selected_strains = {}
        for _, row in test_df.iterrows():
            selected_strains[row["Species"]] = row["Strain"]

    selection_report_path = print_selection_report(selected_strains, output_dir)
    del selection_report_path

    results: List[Dict[str, Any]] = []
    for species, strain in selected_strains.items():
        print(f"Evaluating {species} (Strain: {strain})...")
        env_strategy = environment if environment else "E1"

        prepared_segments = load_prepared_segments_metadata()
        manifest_matches = sorted((DATASET_ROOT / "folds").glob(f"fold_*_{strain.replace(' ', '_')}.json"))
        if manifest_matches and prepared_segments:
            manifest = json.loads(manifest_matches[0].read_text())
            query_group = build_query_group_from_manifest(manifest.get("query_image_ids", []), prepared_segments)
            test_sets = collect_testsets_from_images(query_group) if query_group else []
        else:
            test_sets = collect_testset(
                client=client,
                collection_name=collection_name,
                strain=strain,
                environment_strategy=env_strategy,
            )

        if not test_sets:
            print(f"  No test sets found for {strain} with strategy {env_strategy}")
            continue

        print(f"  Found {len(test_sets)} test sets for {strain}")
        for i, test_group in enumerate(test_sets):
            ids = [img.get("image_id", "?") for img in test_group]
            segments = sorted(set(
                re.search(r"segment_(\d+)", img_id).group(1) if re.search(r"segment_(\d+)", img_id) else "?"
                for img_id in ids
            ))
            angles = sorted(set(img.get("angle", "?") for img in test_group))
            envs = sorted(set(img.get("environment", "?") for img in test_group))
            print(f"    test_set_{i}: {len(ids)} images, segments={segments}, angles={angles}, envs={envs}")
            res = predict_segment_group(
                client=client,
                collection_name=collection_name,
                test_group=test_group,
                strain=strain,
                feature_extractor=feature_extractor,
                k=k,
                min_samples=min_samples,
                without_siblings=without_siblings,
                environment=environment,
                strategy=strategy,
            )
            res["test_set_index"] = i
            res["environment_strategy"] = env_strategy
            results.append(res)

    report_path = print_prediction_results(
        results,
        output_dir,
        collection_name=collection_name,
        k=k,
        media=environment,
        strategy=strategy,
    )
    draw_confusion_matrix(results, os.path.join(output_dir, "confusion_matrix.png"))

    csv_path = write_evaluation_csv(
        results=results,
        output_dir=output_dir,
        feature_extractor=feature_extractor,
        media=environment,
        strategy=strategy,
        collection_name=collection_name,
        k=k,
    )
    if csv_path:
        print(f"CSV saved to: {csv_path}")

    if generate_visualizations and results:
        print("\nGenerating visualizations...")

        correct_dir = os.path.join(output_dir, "visualizations", "correct")
        os.makedirs(correct_dir, exist_ok=True)
        correct_results = [r for r in results if r["correct"]]
        if correct_results:
            print(f"  Visualizing {len(correct_results)} correct predictions...")
            batch_visualize_predictions(
                prediction_results=correct_results,
                segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
                output_dir=correct_dir,
                k=k,
                filter_correct=True,
                max_visualizations=None,
            )

        incorrect_dir = os.path.join(output_dir, "visualizations", "incorrect")
        os.makedirs(incorrect_dir, exist_ok=True)
        incorrect_results = [r for r in results if not r["correct"]]
        if incorrect_results:
            print(f"  Visualizing {len(incorrect_results)} incorrect predictions...")
            batch_visualize_predictions(
                prediction_results=incorrect_results,
                segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
                output_dir=incorrect_dir,
                k=k,
                filter_correct=False,
                max_visualizations=None,
            )

        print(
            f"  Visualizations saved to: {os.path.join(output_dir, 'visualizations')}"
        )

    return results, report_path


def run_comprehensive_report(
    identifier: str,
    extractors: List[str],
    env_strategies: List[str],
    agg_strategies: List[str],
    k: int = 5,
    max_visualizations: int = 20,
    visualize_correct: bool = True,
    visualize_incorrect: bool = True,
    collection_name: str = 'qdrant-research',
    output_root: Path | None = None,
) -> Path:
    """Run a multi-configuration retrieval benchmark and optional visualization."""
    from src.analysis.visualization.visualize_prediction import (
        batch_visualize_predictions,
    )
    from src.config import QDRANT_API_KEY, QDRANT_URL

    print(f"Starting Comprehensive Report: {identifier}")
    print(f"Extractors: {extractors}")
    print(f"Environment Strategies: {env_strategies}")
    print(f"Aggregation Strategies: {agg_strategies}")
    print(f"K: {k}")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_output_dir = output_root or (RESULTS_DIR / f"retrieval_{timestamp}")
    base_output_dir.mkdir(parents=True, exist_ok=True)

    for ext_name in extractors:
        extractor = get_extractor_by_name(ext_name)
        if not extractor:
            print(f"Warning: Unknown extractor {ext_name}, skipping.")
            continue

        for env_strat in env_strategies:
            for agg_strat in agg_strategies:
                segmentation_label = normalize_segmentation_label(collection_name, identifier)
                subfolder_name = f"{ext_name}_{k}_{agg_strat}_{env_strat}_{segmentation_label}"
                output_dir = base_output_dir / subfolder_name
                output_dir.mkdir(parents=True, exist_ok=True)

                if env_strat == "E1":
                    environment_param = None
                elif env_strat == "E2":
                    environment_param = "all"
                else:
                    environment_param = env_strat

                print(f"\\nRunning evaluation for: {subfolder_name}")
                results, _ = run_species_evaluation(
                    client=client,
                    collection_name=collection_name,
                    feature_extractor=extractor,
                    k=k,
                    without_siblings=True,
                    environment=environment_param,
                    strategy=agg_strat,
                    output_dir=str(output_dir),
                )

                if visualize_correct:
                    batch_visualize_predictions(
                        prediction_results=results,
                        segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
                        output_dir=str(output_dir / "visualizations" / "correct"),
                        k=k,
                        filter_correct=True,
                        max_visualizations=max_visualizations,
                    )

                if visualize_incorrect:
                    batch_visualize_predictions(
                        prediction_results=results,
                        segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
                        output_dir=str(output_dir / "visualizations" / "incorrect"),
                        k=k,
                        filter_correct=False,
                        max_visualizations=max_visualizations,
                    )

    return base_output_dir


def run_ensemble_analysis() -> None:

    """Execute ensemble analysis workflow from retrieval experiment."""
    from src.experiments.retrieval import ensemble_analysis

    ensemble_analysis.main()


def run_ensemble_report(strategy: str = "weighted") -> None:
    """Generate detailed ensemble report for one strategy."""
    from src.analysis.retrieval.ensemble_report import (
        create_detailed_comparison_chart,
        load_ensemble_results,
        print_detailed_report,
    )

    results_dir = RESULTS_DIR / "ensemble_analysis"
    json_path = str(results_dir / f"ensemble_results_{strategy}.json")
    output_path = str(results_dir / f"detailed_comparison_{strategy}.png")

    print(f"Loading ensemble results for strategy: {strategy}")
    results = load_ensemble_results(json_path)
    print_detailed_report(results)
    create_detailed_comparison_chart(results, output_path)


def run_compare_ensemble_strategies() -> None:
    """Compare weighted and simple-average ensemble predictions."""
    from src.analysis.retrieval.compare_ensemble_strategies import compare_strategies

    compare_strategies()


ALL_EXTRACTORS = [
    "efficientnetb1_finetuned",
    "resnet50_finetuned",
    "mobilenetv2_finetuned",
    "efficientnetb1",
    "resnet50",
    "mobilenetv2",
    "hog",
    "gabor",
    "colorhistogram",
    "colorhistogramhs",
]

ALL_ENVS = [
    "E1", "E2",
    "E3_CREA", "E3_DG18", "E3_MEA", "E3_YES",
    "E4_CREA", "E4_DG18", "E4_MEA", "E4_YES",
]

ALL_AGGS = [
    "weighted", "uni", "relative", "per_species_avg",
    "max_score", "perquery_avg", "perquery_norm_avg", "freq_strength",
]

ALL_K = [3, 5, 7, 11, 13, 15]


def _resolve_list(values: list[str], catalog: list[str]) -> list[str]:
    if values == ["all"]:
        return catalog
    seen = set()
    resolved = []
    for v in values:
        if v not in seen:
            seen.add(v)
            resolved.append(v)
    return resolved


def _parse_k_minimal(raw: str) -> list[int]:
    result = []
    for chunk in raw.replace(",", " ").split():
        chunk = chunk.strip()
        if "-" in chunk:
            lo_s, hi_s = chunk.split("-", 1)
            result.extend(range(int(lo_s), int(hi_s) + 1))
        else:
            result.append(int(chunk))
    return result


def _resolve_k(values: list[str]) -> list[int]:
    if values == ["all"]:
        return ALL_K
    return sorted(set(_parse_k_minimal(" ".join(values))))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Retrieval experiment runner")
    subparsers = parser.add_subparsers(dest="command")

    comprehensive = subparsers.add_parser(
        "comprehensive", help="Run multi-extractor comprehensive retrieval report"
    )
    comprehensive.add_argument(
        "--identifier",
        type=str,
        default=f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Unique identifier for this run",
    )
    comprehensive.add_argument(
        "--extractors",
        nargs="+",
        default=ALL_EXTRACTORS,
    )
    comprehensive.add_argument(
        "--env_strategies",
        nargs="+",
        default=ALL_ENVS,
    )
    comprehensive.add_argument(
        "--agg_strategies",
        nargs="+",
        default=ALL_AGGS,
    )
    comprehensive.add_argument(
        "--k",
        nargs="+",
        default=ALL_K,
        help="K values (space-separated integers or ranges like 3-7). Use 'all' for [3,5,7,11,13,15]",
    )
    comprehensive.add_argument("--collection-name", type=str, default="qdrant-research")
    comprehensive.add_argument("--output-root", type=Path, default=None)
    comprehensive.add_argument("--max_visualizations", type=int, default=20)
    comprehensive.add_argument(
        "--no-viz-correct",
        action="store_false",
        dest="visualize_correct",
    )
    comprehensive.add_argument(
        "--no-viz-incorrect",
        action="store_false",
        dest="visualize_incorrect",
    )
    comprehensive.set_defaults(visualize_correct=True, visualize_incorrect=True)

    subparsers.add_parser("ensemble-analysis")

    ensemble_report = subparsers.add_parser("ensemble-report")
    ensemble_report.add_argument(
        "--strategy",
        type=str,
        default="weighted",
        choices=["weighted", "simple_avg", "manual_weighted"],
    )

    subparsers.add_parser("ensemble-compare")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "comprehensive":
        extractors = _resolve_list(args.extractors, ALL_EXTRACTORS)
        envs = _resolve_list(args.env_strategies, ALL_ENVS)
        aggs = _resolve_list(args.agg_strategies, ALL_AGGS)
        k_values = _resolve_k(args.k)

        print(f"Extractors: {extractors}")
        print(f"Envs     : {envs}")
        print(f"Aggs     : {aggs}")
        print(f"K values : {k_values}")
        print(f"Total configs: {len(extractors) * len(envs) * len(aggs) * len(k_values)}")

        base_root = args.output_root
        for k_val in k_values:
            print(f"\n=== K = {k_val} ===")
            run_comprehensive_report(
                identifier=args.identifier,
                extractors=extractors,
                env_strategies=envs,
                agg_strategies=aggs,
                k=k_val,
                max_visualizations=args.max_visualizations,
                visualize_correct=args.visualize_correct,
                visualize_incorrect=args.visualize_incorrect,
                collection_name=args.collection_name,
                output_root=base_root,
            )
        return

    if args.command == "ensemble-analysis":
        run_ensemble_analysis()
        return

    if args.command == "ensemble-report":
        run_ensemble_report(strategy=args.strategy)
        return

    if args.command == "ensemble-compare":
        run_compare_ensemble_strategies()
        return

    parser.print_help()


__all__ = [
    "aggregate_predictions",
    "collect_testset",
    "draw_confusion_matrix",
    "filter_siblings",
    "find_neighbors",
    "get_all_images_for_strain",
    "get_extractor_by_name",
    "load_strain_to_species_mapping",
    "predict",
    "predict_segment_group",
    "run_compare_ensemble_strategies",
    "run_comprehensive_report",
    "run_ensemble_analysis",
    "run_ensemble_report",
    "run_species_evaluation",
    "write_evaluation_csv",
    "ExperimentParams",
    "ExperimentResult",
    "run",
]


if __name__ == "__main__":
    main()


@dataclass
class ExperimentParams:
    run_id: str
    output_root: str
    description: str


@dataclass
class ExperimentResult:
    f1_score: float
    strategy_name: str
    artifact_paths: list
    run_id: str


def run(params: ExperimentParams) -> ExperimentResult:
    """Execute one retrieval experiment run scoped to params.output_root."""
    import json
    from pathlib import Path as _Path

    output_root = _Path(params.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    log_dir = output_root / "log"
    log_dir.mkdir(exist_ok=True)

    try:
        from src.config import QDRANT_API_KEY, QDRANT_URL

        from qdrant_client import QdrantClient as _QC

        client = _QC(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        extractor = get_extractor_by_name("resnet50")
        if extractor is None:
            raise ValueError("resnet50 extractor unavailable")
        results, report_path = run_species_evaluation(
            client=client,
            collection_name='qdrant-research',
            feature_extractor=extractor,
            output_dir=str(output_root / "artifacts"),
        )
        correct = sum(1 for r in results if r.get("correct", False))
        total = len(results)
        f1 = correct / total if total > 0 else 0.0
        strategy_name = params.description[:30] if params.description else "retrieval"
        artifact_paths = [str(output_root / "artifacts")]
    except Exception as exc:
        error_log = log_dir / "run.log"
        error_log.write_text(str(exc))
        raise

    result_data = {
        "f1_score": f1,
        "strategy_name": strategy_name,
        "artifact_paths": artifact_paths,
        "run_id": params.run_id,
    }
    results_json = output_root / "results.json"
    results_json.write_text(json.dumps(result_data, indent=2))
    artifact_paths = [str(p) for p in artifact_paths] + [str(results_json)]

    return ExperimentResult(
        f1_score=f1,
        strategy_name=strategy_name,
        artifact_paths=artifact_paths,
        run_id=params.run_id,
    )
