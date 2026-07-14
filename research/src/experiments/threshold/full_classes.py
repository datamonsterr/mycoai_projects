from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from qdrant_client import QdrantClient

from src.config import (
    NEW_DATA_PREPARED_DATASET_DIR,
    ORIGINAL_PREPARED_DATASET_DIR,
    QDRANT_API_KEY,
    QDRANT_URL,
    RESULTS_DIR,
    STRAIN_SPECIES_MAPPING_PATH,
    WORKSPACE_ROOT,
)
from src.experiments.feature_extraction.feature_extractors import (
    EfficientNetB1FinetunedExtractor,
)
from src.experiments.threshold.expanded_threshold_analysis import generate_formulas
from src.utils.qdrant_query import build_filter

OUTPUT_DIR = RESULTS_DIR / "threshold_full_classes"
ANALYTICS_DIR = OUTPUT_DIR / "analytics"
FEATURES_CACHE = OUTPUT_DIR / "features_query_cache.json"
GROUPED_SETS_JSON = OUTPUT_DIR / "grouped_query_sets.json"
SEGMENT_NEIGHBORS_JSON = OUTPUT_DIR / "segment_neighbors.json"
ALL_EXPERIMENTS_CSV = OUTPUT_DIR / "all_experiments.csv"
BEST_STRATEGY_JSON = OUTPUT_DIR / "best_strategy.json"
METRICS_SUMMARY_JSON = OUTPUT_DIR / "metrics_summary.json"
RETRIEVAL_RESULTS_CSV = OUTPUT_DIR / "retrieval_results.csv"
RUN_LOG = OUTPUT_DIR / "run.log"

COLLECTION = "original_yolo_effb1ft"
EXTRACTOR_KEY = "efficientnetb1_finetuned"
K = 11
TOP_N = 5
TEST_CONFIGS = [
    (0, "ob"),
    (0, "rev"),
    (1, "ob"),
    (1, "rev"),
    (2, "ob"),
    (2, "rev"),
]
KNOWN_SPECIES_SLUGS = {
    "aurantiogriseum",
    "freii",
    "melanoconidium",
    "neoechinulatum",
    "polonicum",
    "tricolor",
    "viridicatum",
}


def slugify_species(species: str) -> str:
    label = species.strip().lower()
    if label.startswith("penicillium "):
        label = label[len("penicillium ") :]
    return label.replace(" ", "-")


def strain_to_slug(strain: str) -> str:
    return strain.strip().lower().replace(" ", "-")


def normalize_qdrant_strain(strain: str) -> str:
    return strain.strip().replace("-", " ")


def read_strain_mapping() -> tuple[dict[str, str], set[str]]:
    mapping: dict[str, str] = {}
    test_strains: set[str] = set()
    with open(STRAIN_SPECIES_MAPPING_PATH, newline="") as f:
        for row in csv.DictReader(f):
            strain = row["Strain"].strip()
            mapping[strain] = row["Species"].strip()
            if row.get("Test", "").strip() == "True":
                test_strains.add(strain)
    return mapping, test_strains


def canonical_species_label(label: str) -> str:
    return slugify_species(label)


def collect_segments_for_strain_dir(strain_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for env_dir in sorted(strain_dir.iterdir()):
        if not env_dir.is_dir():
            continue
        for angle_dir in sorted(env_dir.iterdir()):
            if not angle_dir.is_dir():
                continue
            seg_dir = angle_dir / "segments_yolo"
            if not seg_dir.is_dir():
                continue
            for seg_idx, seg_path in enumerate(sorted(seg_dir.glob("segment_*.jpg"))):
                try:
                    rel = seg_path.relative_to(WORKSPACE_ROOT)
                except ValueError:
                    rel = seg_path
                candidates.append(
                    {
                        "segment_id": "__".join(str(p) for p in seg_path.relative_to(strain_dir.parent.parent.parent).parts).removesuffix(".jpg"),
                        "image_path": str(seg_path),
                        "image_path_rel": str(rel),
                        "environment": env_dir.name.upper(),
                        "angle": angle_dir.name.lower(),
                        "segment_index": seg_idx,
                    }
                )
    return candidates


def collect_six_sets(segment_candidates: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    env_segment_angle: dict[str, dict[int, dict[str, list[dict[str, Any]]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for img in segment_candidates:
        env_segment_angle[img["environment"]][int(img["segment_index"])][img["angle"]].append(img)
    if not env_segment_angle:
        return []
    used_by_env: dict[str, set[tuple[str, str]]] = defaultdict(set)
    test_sets: list[list[dict[str, Any]]] = []
    angle_aliases = {"ob": ["ob", "obverse"], "rev": ["rev", "reverse"]}
    for wanted_idx, wanted_angle in TEST_CONFIGS:
        test_set: list[dict[str, Any]] = []
        for env in sorted(env_segment_angle):
            pool = env_segment_angle[env]
            chosen: dict[str, Any] | None = None
            if wanted_idx in pool:
                for ang in angle_aliases[wanted_angle]:
                    for candidate in pool[wanted_idx].get(ang, []):
                        key = (candidate["image_path_rel"], candidate["angle"])
                        if key not in used_by_env[env]:
                            chosen = candidate
                            break
                    if chosen is not None:
                        break
            if chosen is None:
                for seg_idx in sorted(pool):
                    for ang in sorted(pool[seg_idx]):
                        for candidate in pool[seg_idx][ang]:
                            key = (candidate["image_path_rel"], candidate["angle"])
                            if key not in used_by_env[env]:
                                chosen = candidate
                                break
                        if chosen is not None:
                            break
                    if chosen is not None:
                        break
            if chosen is None:
                break
            used_by_env[env].add((chosen["image_path_rel"], chosen["angle"]))
            test_set.append(chosen)
        if test_set and len(test_set) == len(env_segment_angle):
            test_sets.append(test_set)
    return test_sets


def build_grouped_query_sets() -> list[dict[str, Any]]:
    strain_mapping, test_strains = read_strain_mapping()
    grouped: list[dict[str, Any]] = []
    for strain in sorted(test_strains):
        species_full = strain_mapping[strain]
        species_slug = canonical_species_label(species_full)
        strain_dir = ORIGINAL_PREPARED_DATASET_DIR / f"penicillium-{species_slug}" / strain_to_slug(strain)
        if not strain_dir.is_dir():
            continue
        test_sets = collect_six_sets(collect_segments_for_strain_dir(strain_dir))
        for idx, test_set in enumerate(test_sets, start=1):
            grouped.append(
                {
                    "sample_id": f"known::{strain_to_slug(strain)}::set{idx}",
                    "strain": strain,
                    "species_label": species_full,
                    "species_slug": species_slug,
                    "is_known": 1,
                    "test_set_index": idx,
                    "segments": test_set,
                }
            )
    for species_dir in sorted(NEW_DATA_PREPARED_DATASET_DIR.iterdir()):
        if not species_dir.is_dir():
            continue
        species_slug = species_dir.name.lower()
        for strain_dir in sorted(species_dir.iterdir()):
            if not strain_dir.is_dir():
                continue
            test_sets = collect_six_sets(collect_segments_for_strain_dir(strain_dir))
            is_known = 1 if species_slug in KNOWN_SPECIES_SLUGS else 0
            for idx, test_set in enumerate(test_sets, start=1):
                grouped.append(
                    {
                        "sample_id": f"incoming::{species_slug}::{strain_dir.name}::set{idx}",
                        "strain": strain_dir.name.upper(),
                        "species_label": species_slug,
                        "species_slug": species_slug,
                        "is_known": is_known,
                        "test_set_index": idx,
                        "segments": test_set,
                    }
                )
    return grouped


def extract_feature_cache(grouped_sets: list[dict[str, Any]], force: bool = False) -> dict[str, dict[str, Any]]:
    if FEATURES_CACHE.exists() and not force:
        with open(FEATURES_CACHE) as f:
            data = json.load(f)
        return {item["image_path_rel"]: item for item in data}
    extractor = EfficientNetB1FinetunedExtractor()
    cache: dict[str, dict[str, Any]] = {}
    for grouped in grouped_sets:
        for seg in grouped["segments"]:
            key = seg["image_path_rel"]
            if key in cache:
                continue
            image = cv2.imread(seg["image_path"])
            if image is None:
                continue
            vector = extractor.extract(image).tolist()
            cache[key] = {
                "image_path": seg["image_path"],
                "image_path_rel": key,
                "environment": seg["environment"],
                "angle": seg["angle"],
                "segment_index": seg["segment_index"],
                "vector": vector,
            }
    with open(FEATURES_CACHE, "w") as f:
        json.dump(list(cache.values()), f)
    return cache


def query_segment_neighbors(grouped_sets: list[dict[str, Any]], feature_cache: dict[str, dict[str, Any]], collection: str, force: bool = False) -> dict[str, list[dict[str, Any]]]:
    if SEGMENT_NEIGHBORS_JSON.exists() and not force:
        with open(SEGMENT_NEIGHBORS_JSON) as f:
            return json.load(f)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=120)
    cache: dict[str, list[dict[str, Any]]] = {}
    for grouped in grouped_sets:
        exclude_strain = normalize_qdrant_strain(grouped["strain"]) if grouped["is_known"] else None
        for seg in grouped["segments"]:
            key = seg["image_path_rel"]
            if key in cache or key not in feature_cache:
                continue
            search_filter = build_filter(environment=seg["environment"], exclude_strain=exclude_strain)
            response = client.query_points(
                collection_name=collection,
                query=feature_cache[key]["vector"],
                using=EXTRACTOR_KEY,
                query_filter=search_filter,
                limit=K,
                with_payload=True,
            )
            neighbors: list[dict[str, Any]] = []
            for point in response.points:
                payload = point.payload or {}
                neighbors.append(
                    {
                        "species": canonical_species_label(payload.get("specy") or payload.get("species") or "unknown"),
                        "score": float(point.score),
                        "strain": str(payload.get("strain", "")),
                        "environment": str(payload.get("environment", "")),
                    }
                )
            cache[key] = neighbors
    with open(SEGMENT_NEIGHBORS_JSON, "w") as f:
        json.dump(cache, f)
    return cache


def _segment_species_scores(neighbors: list[dict[str, Any]]) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for item in neighbors:
        totals[item["species"]] += float(item["score"])
    total = sum(totals.values()) or 1.0
    return {species: score / total for species, score in totals.items()}


def aggregate_group_scores(grouped: dict[str, Any], segment_neighbors: dict[str, list[dict[str, Any]]], aggregator: str) -> list[dict[str, float]]:
    seg_maps: list[dict[str, float]] = []
    all_neighbors: list[dict[str, Any]] = []
    for seg in grouped["segments"]:
        neighbors = segment_neighbors.get(seg["image_path_rel"], [])
        if not neighbors:
            continue
        all_neighbors.extend(neighbors)
        seg_maps.append(_segment_species_scores(neighbors))
    if not seg_maps:
        return []
    totals: dict[str, float] = defaultdict(float)
    if aggregator == "weighted_sum":
        for item in all_neighbors:
            totals[item["species"]] += float(item["score"])
    elif aggregator == "mean_segment":
        species = {sp for seg_map in seg_maps for sp in seg_map}
        for sp in species:
            totals[sp] = float(np.mean([seg_map.get(sp, 0.0) for seg_map in seg_maps]))
    elif aggregator == "max_segment":
        species = {sp for seg_map in seg_maps for sp in seg_map}
        for sp in species:
            totals[sp] = max(seg_map.get(sp, 0.0) for seg_map in seg_maps)
    else:
        raise ValueError(f"Unknown aggregator: {aggregator}")
    total = sum(totals.values()) or 1.0
    ranked = sorted(
        ({"species": sp, "score": score / total} for sp, score in totals.items()),
        key=lambda item: item["score"],
        reverse=True,
    )
    return ranked[:TOP_N]


def build_rows(grouped_sets: list[dict[str, Any]], segment_neighbors: dict[str, list[dict[str, Any]]], aggregator: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for grouped in grouped_sets:
        ranked = aggregate_group_scores(grouped, segment_neighbors, aggregator)
        if not ranked:
            continue
        row: dict[str, Any] = {
            "sample_id": grouped["sample_id"],
            "strain": grouped["strain"],
            "species_label": grouped["species_label"],
            "species_slug": grouped["species_slug"],
            "is_known": grouped["is_known"],
            "test_set_index": grouped["test_set_index"],
            "aggregator": aggregator,
            "predicted_species": ranked[0]["species"],
            "segment_count": len(grouped["segments"]),
            "environment": ",".join(sorted({seg["environment"] for seg in grouped["segments"]})),
            "image_path": ";".join(seg["image_path_rel"] for seg in grouped["segments"]),
        }
        for i in range(TOP_N):
            if i < len(ranked):
                row[f"s{i}_score"] = float(ranked[i]["score"])
                row[f"s{i}_species"] = ranked[i]["species"]
            else:
                row[f"s{i}_score"] = 0.0
                row[f"s{i}_species"] = ""
        rows.append(row)
    return rows


def compute_confusion(rows: list[dict[str, Any]], scores: np.ndarray, threshold: float) -> dict[str, float]:
    tp = fp = tn = fn = 0
    for row, score in zip(rows, scores, strict=False):
        accept = float(score) >= float(threshold)
        is_known = int(row["is_known"]) == 1
        pred_species = canonical_species_label(str(row["predicted_species"]))
        gt_species = canonical_species_label(str(row["species_label"]))
        if is_known:
            if accept and pred_species == gt_species:
                tp += 1
            else:
                fn += 1
        else:
            if accept:
                fp += 1
            else:
                tn += 1
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "specificity": specificity,
    }


def threshold_grid(scores: np.ndarray, rows: list[dict[str, Any]], steps: int = 500) -> tuple[float, dict[str, float]]:
    lo, hi = float(np.percentile(scores, 1)), float(np.percentile(scores, 99))
    if lo >= hi:
        metrics = compute_confusion(rows, scores, lo)
        return lo, metrics
    best_t = lo
    best_metrics = compute_confusion(rows, scores, lo)
    for threshold in np.linspace(lo, hi, steps):
        metrics = compute_confusion(rows, scores, float(threshold))
        if metrics["f1"] > best_metrics["f1"]:
            best_t = float(threshold)
            best_metrics = metrics
    return best_t, best_metrics


def threshold_j(scores: np.ndarray, rows: list[dict[str, Any]], steps: int = 500) -> tuple[float, dict[str, float]]:
    lo, hi = float(np.percentile(scores, 1)), float(np.percentile(scores, 99))
    if lo >= hi:
        metrics = compute_confusion(rows, scores, lo)
        return lo, metrics
    best_t = lo
    best_metrics = compute_confusion(rows, scores, lo)
    best_j = best_metrics["recall"] - (1.0 - best_metrics["specificity"])
    for threshold in np.linspace(lo, hi, steps):
        metrics = compute_confusion(rows, scores, float(threshold))
        j_score = metrics["recall"] - (1.0 - metrics["specificity"])
        if j_score > best_j:
            best_j = j_score
            best_t = float(threshold)
            best_metrics = metrics
    return best_t, best_metrics


def threshold_otsu(scores: np.ndarray, rows: list[dict[str, Any]], bins: int = 512) -> tuple[float, dict[str, float]]:
    lo, hi = float(np.percentile(scores, 1)), float(np.percentile(scores, 99))
    if lo >= hi:
        metrics = compute_confusion(rows, scores, lo)
        return lo, metrics
    thresholds = np.linspace(lo, hi, bins)
    best_t = lo
    best_var = math.inf
    for threshold in thresholds:
        below = scores < threshold
        above = ~below
        if not above.any() or not below.any():
            continue
        var = float(scores[above].var()) * float(above.mean()) + float(scores[below].var()) * float(below.mean())
        if var < best_var:
            best_var = var
            best_t = float(threshold)
    return best_t, compute_confusion(rows, scores, best_t)


def write_rows_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = [
        "sample_id",
        "strain",
        "species_label",
        "species_slug",
        "is_known",
        "test_set_index",
        "aggregator",
        "predicted_species",
        "segment_count",
        "environment",
        "image_path",
    ] + [item for i in range(TOP_N) for item in (f"s{i}_score", f"s{i}_species")]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(collection: str = COLLECTION, force: bool = False) -> dict[str, Any]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    grouped_sets = build_grouped_query_sets()
    with open(GROUPED_SETS_JSON, "w") as f:
        json.dump(grouped_sets, f)
    feature_cache = extract_feature_cache(grouped_sets, force=force)
    segment_neighbors = query_segment_neighbors(grouped_sets, feature_cache, collection=collection, force=force)
    experiments: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    algorithms = {
        "f1_grid": threshold_grid,
        "roc_opt": threshold_j,
        "otsu": threshold_otsu,
    }
    for aggregator in ("weighted_sum", "mean_segment", "max_segment"):
        rows = build_rows(grouped_sets, segment_neighbors, aggregator)
        if not rows:
            continue
        score_matrix = np.array([[float(row.get(f"s{i}_score", 0.0)) for i in range(TOP_N)] for row in rows], dtype=float)
        formulas = generate_formulas(score_matrix)
        for formula_name, formula_scores in formulas.items():
            if float(np.std(formula_scores)) < 1e-8:
                continue
            for algo_name, algo_fn in algorithms.items():
                threshold, metrics = algo_fn(formula_scores, rows)
                result = {
                    "aggregator": aggregator,
                    "formula": formula_name,
                    "algorithm": algo_name,
                    "threshold": threshold,
                    **metrics,
                }
                experiments.append(result)
                if best is None or result["f1"] > best["f1"]:
                    best = result
    if best is None:
        raise RuntimeError("No threshold_full_classes experiments produced results")
    with open(ALL_EXPERIMENTS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["aggregator", "formula", "algorithm", "threshold", "tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity"])
        writer.writeheader()
        writer.writerows(experiments)
    best_retrieval_rows = build_rows(grouped_sets, segment_neighbors, str(best["aggregator"]))
    write_rows_csv(best_retrieval_rows, RETRIEVAL_RESULTS_CSV)
    top10 = sorted(experiments, key=lambda item: item["f1"], reverse=True)[:10]
    with open(BEST_STRATEGY_JSON, "w") as f:
        json.dump(best, f, indent=2)
    metrics_summary = {
        "grouped_query_sets": len(grouped_sets),
        "feature_cache_segments": len(feature_cache),
        "neighbor_cache_segments": len(segment_neighbors),
        "experiment_count": len(experiments),
        "best": best,
    }
    with open(METRICS_SUMMARY_JSON, "w") as f:
        json.dump(metrics_summary, f, indent=2)
    with open(ANALYTICS_DIR / "top10.json", "w") as f:
        json.dump(top10, f, indent=2)
    with open(ANALYTICS_DIR / "confusion_best.json", "w") as f:
        json.dump({k: best[k] for k in ("tp", "fp", "tn", "fn", "precision", "recall", "f1", "specificity")}, f, indent=2)
    examples = {"tp": [], "fp": [], "tn": [], "fn": []}
    best_formula_scores = generate_formulas(np.array([[float(row.get(f"s{i}_score", 0.0)) for i in range(TOP_N)] for row in best_retrieval_rows], dtype=float))[str(best["formula"])]
    for row, score in zip(best_retrieval_rows, best_formula_scores, strict=False):
        accept = float(score) >= float(best["threshold"])
        is_known = int(row["is_known"]) == 1
        pred_species = canonical_species_label(str(row["predicted_species"]))
        gt_species = canonical_species_label(str(row["species_label"]))
        if is_known and accept and pred_species == gt_species:
            examples["tp"].append(row["sample_id"])
        elif is_known:
            examples["fn"].append(row["sample_id"])
        elif accept:
            examples["fp"].append(row["sample_id"])
        else:
            examples["tn"].append(row["sample_id"])
    with open(ANALYTICS_DIR / "outcome_examples.json", "w") as f:
        json.dump(examples, f, indent=2)
    with open(RUN_LOG, "w") as f:
        f.write(json.dumps(metrics_summary, indent=2))
    return metrics_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Threshold full-classes grouped rerun")
    parser.add_argument("--collection", default=COLLECTION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    summary = run(collection=args.collection, force=args.force)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
