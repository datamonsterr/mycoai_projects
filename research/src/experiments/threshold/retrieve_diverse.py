"""
Step 1: Retrieve diverse dataset images against Qdrant and record similarity scores.

Reads Dataset/diverse_data/diverse_data_metadata.json, groups segmented colonies by
strain into retrieval-style test sets, queries each test set with
EfficientNetB1_finetuned retrieval (same-environment filter, weighted-by-score,
k=11), and writes:

    results/threshold/diverse_retrieval_results.csv

Each row = one segmented test set from the diverse dataset with columns:
    sample_id, strain, test_set_index, species_label, is_known, environment, angle,
    s0_score, s0_species, s1_score, s1_species, ..., s4_score, s4_species,
    predicted_species, correct_species

Usage:
    uv run python -m src.experiments.threshold.retrieve_diverse
    uv run python -m src.experiments.threshold.retrieve_diverse --limit 50
    uv run python -m src.experiments.threshold.retrieve_diverse --resume   # skip already done
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2  # noqa: E402

from src.config import (  # noqa: E402
    COLLECTION_NAME,
    INCOMING_METADATA_PATH,
    CURATED_METADATA_PATH,
    QDRANT_API_KEY,
    QDRANT_URL,
    RESULTS_DIR,
    WORKSPACE_ROOT,
    SEGMENTED_IMAGE_DIR,
)
from src.experiments.feature_extraction.feature_extractors import (  # noqa: E402
    EfficientNetB1FinetunedExtractor,
)
from src.analysis.visualization.visualize_prediction import (  # noqa: E402
    _resolve_image_path,
    visualize_prediction_by_environment,
)
from src.experiments.retrieval.run import (  # noqa: E402
    aggregate_predictions,
    load_strain_to_species_mapping,
)
from src.utils.list_env import get_environment_list  # noqa: E402

# Override: use local Docker Qdrant when env var is unset (defaults to cloud URL)
_qdrant_url = QDRANT_URL
# Use localhost when QDRANT_URL is the cloud default (env var is unset)
if not os.getenv("QDRANT_URL") or "cloud.qdrant" in _qdrant_url:
    _qdrant_url = "http://localhost:6333"

try:
    from qdrant_client import QdrantClient
except ImportError:
    print("ERROR: qdrant_client not installed. Run: uv add qdrant-client")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIVERSE_METADATA_PATH = INCOMING_METADATA_PATH
OUTPUT_DIR = RESULTS_DIR / "threshold"
OUTPUT_CSV = OUTPUT_DIR / "diverse_retrieval_results.csv"
VIS_OUTPUT_DIR = OUTPUT_DIR / "diverse_retrieval_visualizations"
JSON_OUTPUT_DIR = OUTPUT_DIR / "diverse_retrieval_json"

COLLECTION = f"{COLLECTION_NAME}_retrieval"
EXTRACTOR_KEY = "resnet50_finetuned"
K = 11
TOP_N_SCORES = 5


def _load_known_species_map() -> Dict[str, str]:
    """Build mapping from stripped species names to full DB names using curated metadata."""
    if not CURATED_METADATA_PATH.exists():
        return {}
    with open(CURATED_METADATA_PATH) as f:
        curated = json.load(f)
    mapping: Dict[str, str] = {}
    seen = set()
    for item in curated:
        info = item.get("instance_info", item.get("data", {}))
        species_full = info.get("species", "")
        if not species_full or species_full == "unknown":
            continue
        stripped = _strip_penicillium(species_full)
        if stripped and stripped not in seen:
            seen.add(stripped)
            mapping[stripped] = species_full
            mapping[species_full.lower()] = species_full
    return mapping


def _strip_penicillium(label: str) -> str:
    """Remove 'Penicillium ' or 'penicillium ' prefix from species name."""
    clean = label.strip().lower()
    for prefix in ("penicillium ",):
        if clean.startswith(prefix):
            return clean[len(prefix) :]
    return clean


KNOWN_SPECIES_MAP = _load_known_species_map()

CSV_FIELDS = (
    [
        "sample_id",
        "strain",
        "test_set_index",
        "species_label",
        "is_known",
        "environment",
        "angle",
    ]
    + [f"s{i}_score" for i in range(TOP_N_SCORES)]
    + [f"s{i}_species" for i in range(TOP_N_SCORES)]
    + ["predicted_species", "correct_species", "image_path"]
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_known_species(species_label: str) -> bool:
    """Return True if species is known (exists in curated DB)."""
    return map_to_db_species(species_label) is not None


def map_to_db_species(species_label: str) -> Optional[str]:
    """Map incoming species name to DB species name, or None if no match."""
    label = species_label.strip()
    if not label or label.lower() == "unknown":
        return None
    stripped = _strip_penicillium(label)
    if stripped in KNOWN_SPECIES_MAP:
        return KNOWN_SPECIES_MAP[stripped]
    if label.lower() in KNOWN_SPECIES_MAP:
        return KNOWN_SPECIES_MAP[label.lower()]
    return None


def aggregate_weighted(neighbors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregate neighbour scores into a ranked species list (weighted by score).
    Returns list of {"species": ..., "score": ...} sorted descending.
    """
    totals: Dict[str, float] = {}
    for n in neighbors:
        sp = n.get("specy") or n.get("species", "unknown")
        score = float(n.get("score", 0.0))
        totals[sp] = totals.get(sp, 0.0) + score

    # Normalise
    total_weight = sum(totals.values()) or 1.0
    ranked = sorted(
        [{"species": sp, "score": s / total_weight} for sp, s in totals.items()],
        key=lambda x: float(cast(float, x["score"])),
        reverse=True,
    )
    return ranked


def check_qdrant(client: QdrantClient) -> bool:
    """Check if the collection exists and has data."""
    try:
        info = client.get_collection(COLLECTION)
        count = info.points_count or 0
        print(f"  Qdrant collection '{COLLECTION}': {count} points")
        return count > 0
    except Exception as exc:
        print(f"  ERROR: Cannot access Qdrant collection: {exc}")
        return False


def load_done_ids(csv_path: Path) -> set:
    """Load already-processed sample_ids from existing CSV."""
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        return {row["sample_id"] for row in reader}


def safe_filename(value: str) -> str:
    """Convert arbitrary text to a filesystem-safe ASCII-ish filename."""
    cleaned = [ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in value]
    return "".join(cleaned).strip("_") or "item"


def group_images_by_strain(
    images: List[Dict[str, Any]],
) -> List[tuple[str, List[Dict[str, Any]]]]:
    """Return metadata entries grouped by strain while preserving input order."""
    grouped: dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for entry in images:
        info = entry.get("instance_info", entry.get("data", {}))
        strain = info.get("strain") or entry.get("item_id", entry["id"])
        grouped[strain].append(entry)
    return list(grouped.items())


def build_diverse_segment_candidates(
    strain: str,
    strain_entries: List[Dict[str, Any]],
    available_environments: set[str],
) -> List[Dict[str, Any]]:
    """Build per-segment query candidates from incoming metadata."""
    segment_candidates: List[Dict[str, Any]] = []

    for entry in strain_entries:
        source_id = entry.get("item_id", entry.get("id", ""))
        info = entry.get("instance_info", entry.get("data", {}))
        environment = (info.get("environment") or info.get("media", "UNKNOWN")).upper()
        angle = info.get("angle", "UNKNOWN")
        paths = entry.get("paths", {})
        segment_paths = paths.get("segments", [])

        if environment not in available_environments:
            env_set = {e.upper() for e in available_environments}
            if environment not in env_set:
                continue

        if not segment_paths:
            continue

        for segment_index, segment_path_rel in enumerate(segment_paths):
            segment_path = WORKSPACE_ROOT / segment_path_rel
            if not segment_path.exists():
                continue

            segment_candidates.append(
                {
                    "image_id": Path(segment_path_rel).stem,
                    "image_path": str(segment_path),
                    "image_path_rel": str(segment_path_rel),
                    "parent_id": source_id,
                    "segment_index": segment_index,
                    "environment": environment,
                    "angle": angle,
                }
            )

    return segment_candidates


def collect_diverse_testsets(
    segment_candidates: List[Dict[str, Any]],
) -> List[List[Dict[str, Any]]]:
    """Match retrieval test-set logic using diverse segmented query images."""
    env_segment_angle_images: Dict[str, Dict[Any, Dict[Any, List[Dict[str, Any]]]]] = (
        defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    )

    for img in segment_candidates:
        env = img.get("environment", "unknown")
        segment_index = img.get("segment_index", 0)
        angle = img.get("angle", "unknown")
        env_segment_angle_images[env][segment_index][angle].append(img)

    if not env_segment_angle_images:
        return []

    test_sets: List[List[Dict[str, Any]]] = []
    test_configs = [
        (0, "ob"),
        (0, "rev"),
        (1, "ob"),
        (1, "rev"),
        (2, "ob"),
        (2, "rev"),
    ]
    used_image_angle_per_env: Dict[str, set] = defaultdict(set)

    for segment_idx, preferred_angle in test_configs:
        test_set: List[Dict[str, Any]] = []

        for env in sorted(env_segment_angle_images.keys()):
            segment_images = env_segment_angle_images[env]
            img_selected: Optional[Dict[str, Any]] = None

            if segment_idx in segment_images:
                angle_variations = {
                    "ob": ["ob", "obverse"],
                    "rev": ["rev", "reverse"],
                }
                for angle_var in angle_variations.get(
                    preferred_angle, [preferred_angle]
                ):
                    if (
                        angle_var in segment_images[segment_idx]
                        and segment_images[segment_idx][angle_var]
                    ):
                        candidates = segment_images[segment_idx][angle_var]
                        for candidate in candidates:
                            combo_key = (
                                candidate["image_id"],
                                candidate.get("angle", "unknown"),
                            )
                            if combo_key not in used_image_angle_per_env[env]:
                                img_selected = candidate
                                break
                        if img_selected is None and candidates:
                            img_selected = candidates[0]
                        break

                if img_selected is None:
                    for angle in sorted(segment_images[segment_idx].keys()):
                        candidates = segment_images[segment_idx][angle]
                        if candidates:
                            for candidate in candidates:
                                combo_key = (
                                    candidate["image_id"],
                                    candidate.get("angle", "unknown"),
                                )
                                if combo_key not in used_image_angle_per_env[env]:
                                    img_selected = candidate
                                    break
                            if img_selected is None:
                                img_selected = candidates[0]
                            break

            if img_selected is None:
                for seg_idx in sorted(segment_images.keys()):
                    for angle in sorted(segment_images[seg_idx].keys()):
                        candidates = segment_images[seg_idx][angle]
                        if candidates:
                            for candidate in candidates:
                                combo_key = (
                                    candidate["image_id"],
                                    candidate.get("angle", "unknown"),
                                )
                                if combo_key not in used_image_angle_per_env[env]:
                                    img_selected = candidate
                                    break
                            if img_selected is not None:
                                break
                    if img_selected is not None:
                        break

            if img_selected is not None:
                test_set.append(img_selected)
                combo_key = (
                    img_selected["image_id"],
                    img_selected.get("angle", "unknown"),
                )
                used_image_angle_per_env[env].add(combo_key)
            else:
                break

        if test_set and len(test_set) == len(env_segment_angle_images):
            test_sets.append(test_set)

    return test_sets


# ---------------------------------------------------------------------------
# Main retrieval
# ---------------------------------------------------------------------------


def _entry_sort_key(entry: Dict[str, Any]) -> tuple:
    info = entry.get("instance_info", entry.get("data", {}))
    eid = entry.get("item_id", entry.get("id", ""))
    return (info.get("environment", ""), info.get("angle", ""), eid)


def retrieve_diverse(limit: Optional[int] = None, resume: bool = False) -> Path:
    """
    Run retrieval for all diverse-data strains. Returns path to output CSV.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load metadata
    if not DIVERSE_METADATA_PATH.exists():
        print(f"ERROR: Diverse metadata not found: {DIVERSE_METADATA_PATH}")
        print(
            "Run: uv run python src/prepare/reorganize_diverse_data.py --mode pipeline"
        )
        sys.exit(1)

    with open(DIVERSE_METADATA_PATH) as f:
        metadata = json.load(f)

    images = metadata if isinstance(metadata, list) else metadata.get("images", [])
    strain_groups = group_images_by_strain(images)
    print(
        f"Loaded {len(images)} images from incoming metadata across {len(strain_groups)} strains"
    )

    # Resume: skip already-processed
    done_ids: set = set()
    if resume and OUTPUT_CSV.exists():
        done_ids = load_done_ids(OUTPUT_CSV)
        print(f"Resuming: {len(done_ids)} already processed, skipping")

    if limit:
        strain_groups = strain_groups[:limit]

    # Connect to Qdrant
    print(f"\nConnecting to Qdrant: {_qdrant_url}")
    client = QdrantClient(url=_qdrant_url, api_key=QDRANT_API_KEY, timeout=30)
    if not check_qdrant(client):
        print("ERROR: Qdrant not available or collection empty.")
        print("Run: docker compose up -d  (and ensure collection is populated)")
        sys.exit(1)

    available_environments = set(get_environment_list(client, COLLECTION))
    print("Available DB environments: " + ", ".join(sorted(available_environments)))
    strain_to_specy = load_strain_to_species_mapping()

    # Load feature extractor
    print(f"\nLoading extractor: {EXTRACTOR_KEY}")
    extractor = EfficientNetB1FinetunedExtractor()
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    # Open CSV for writing (append if resuming)
    mode = "a" if resume and OUTPUT_CSV.exists() else "w"
    with open(OUTPUT_CSV, mode, newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        if mode == "w":
            writer.writeheader()

        processed = 0
        skipped = 0

        for strain, strain_entries in strain_groups:
            sorted_entries = sorted(strain_entries, key=_entry_sort_key)
            base_info = sorted_entries[0].get(
                "instance_info", sorted_entries[0].get("data", {})
            )
            species_label = base_info.get("species", "UNKNOWN")
            is_known = is_known_species(species_label)
            db_species = map_to_db_species(species_label)

            segment_candidates = build_diverse_segment_candidates(
                strain=strain,
                strain_entries=sorted_entries,
                available_environments=available_environments,
            )
            test_sets = collect_diverse_testsets(segment_candidates)
            if not test_sets:
                print(f"  SKIP {strain}: no segmented test sets could be built")
                continue

            print(f"  Found {len(test_sets)} test sets for {strain}")

            for test_set_index, test_group in enumerate(test_sets, start=1):
                sample_id = f"{strain}__set{test_set_index}"
                if sample_id in done_ids:
                    skipped += 1
                    continue

                raw_results: List[Dict[str, Any]] = []
                query_paths: List[str] = []
                environments: List[str] = []
                angles: List[str] = []
                testset_valid = True

                for query_img in test_group:
                    img_bgr = cv2.imread(query_img["image_path"])
                    if img_bgr is None:
                        print(
                            f"  SKIP {sample_id}: cannot read segment at {query_img['image_path']}"
                        )
                        testset_valid = False
                        break

                    try:
                        features = extractor.extract(img_bgr)
                    except Exception as exc:
                        print(
                            f"  SKIP {sample_id}: feature extraction failed for {query_img['image_id']}: {exc}"
                        )
                        testset_valid = False
                        break

                    environment = query_img.get("environment", "UNKNOWN")
                    env_filter = Filter(
                        must=[
                            FieldCondition(
                                key="environment",
                                match=MatchValue(value=environment),
                            )
                        ],
                        must_not=[
                            FieldCondition(
                                key="strain",
                                match=MatchValue(value=strain),
                            )
                        ],
                    )

                    try:
                        results = client.query_points(
                            collection_name=COLLECTION,
                            query=features.tolist(),
                            using=extractor.name,
                            query_filter=env_filter,
                            limit=K,
                            with_payload=True,
                        )
                    except Exception as exc:
                        print(
                            f"  SKIP {sample_id}: Qdrant search failed for {query_img['image_id']}: {exc}"
                        )
                        testset_valid = False
                        break

                    query_neighbors: List[Dict[str, Any]] = []
                    for hit in results.points:
                        payload = hit.payload or {}
                        image_id = payload.get("image_id") or payload.get("id", "")
                        query_neighbors.append(
                            {
                                "image_id": image_id,
                                "image_path": _resolve_image_path(
                                    {
                                        "image_id": image_id,
                                        "image_path": payload.get("segment_path"),
                                    },
                                    str(SEGMENTED_IMAGE_DIR),
                                    "image_id",
                                ),
                                "specy": payload.get("specy", "unknown"),
                                "score": hit.score,
                                "strain": payload.get("strain", ""),
                                "environment": payload.get("environment", ""),
                                "angle": payload.get("angle", ""),
                                "parent_id": payload.get("parent_id", ""),
                                "segment_index": payload.get("segment_index", -1),
                            }
                        )

                    if not query_neighbors:
                        print(
                            f"  SKIP {sample_id}: no neighbors found for {query_img['image_id']}"
                        )
                        testset_valid = False
                        break

                    environments.append(environment)
                    angles.append(query_img.get("angle", "UNKNOWN"))
                    query_paths.append(query_img["image_path_rel"])
                    raw_results.append(
                        {
                            "query_image_id": query_img["image_id"],
                            "query_image_path": query_img["image_path"],
                            "query_parent_id": query_img["parent_id"],
                            "query_environment": environment,
                            "query_angle": query_img.get("angle", "UNKNOWN"),
                            "query_segment_index": query_img.get("segment_index", -1),
                            "neighbors": query_neighbors,
                        }
                    )

                if not testset_valid or not raw_results:
                    continue

                aggregated = aggregate_predictions(
                    raw_results,
                    strain_to_specy,
                    K,
                    min_samples=None,
                    strategy="weighted",
                )
                ranked = [
                    {"species": species, "score": score}
                    for species, score in aggregated
                ]

                row: Dict[str, Any] = {
                    "sample_id": sample_id,
                    "strain": strain,
                    "test_set_index": test_set_index,
                    "species_label": species_label,
                    "is_known": int(is_known),
                    "environment": ",".join(sorted(set(environments))),
                    "angle": ",".join(sorted(set(angles))),
                    "predicted_species": ranked[0]["species"] if ranked else "unknown",
                    "correct_species": db_species or "",
                    "image_path": ";".join(query_paths),
                }

                for i in range(TOP_N_SCORES):
                    if i < len(ranked):
                        row[f"s{i}_score"] = f"{ranked[i]['score']:.6f}"
                        row[f"s{i}_species"] = ranked[i]["species"]
                    else:
                        row[f"s{i}_score"] = ""
                        row[f"s{i}_species"] = ""

                writer.writerow(row)
                csvfile.flush()

                predicted_specy = ranked[0]["species"] if ranked else "unknown"
                predicted_confidence = ranked[0]["score"] if ranked else 0.0
                is_correct = bool(
                    is_known
                    and db_species
                    and (
                        predicted_specy == db_species
                        or _strip_penicillium(predicted_specy)
                        == _strip_penicillium(db_species)
                    )
                )

                prediction_result: Dict[str, Any] = {
                    "ground_truth": db_species or species_label,
                    "predicted_specy": predicted_specy,
                    "correct": is_correct,
                    "predicted_confidence": predicted_confidence,
                    "feature_extractor": EXTRACTOR_KEY,
                    "strategy": "weighted",
                    "strain": strain,
                    "test_set_index": test_set_index,
                    "species_label": species_label,
                    "raw_results": raw_results,
                    "aggregated_results": [
                        {"specy": r["species"], "score": r["score"]} for r in ranked
                    ],
                    "query_count": len(raw_results),
                    "environments": sorted(set(environments)),
                }

                vis_output_path = (
                    VIS_OUTPUT_DIR
                    / ("correct" if is_correct else "incorrect")
                    / f"vis_{safe_filename(strain)}_set{test_set_index}.jpg"
                )
                try:
                    visualize_prediction_by_environment(
                        prediction_result=prediction_result,
                        segmented_image_dir=str(SEGMENTED_IMAGE_DIR),
                        output_path=str(vis_output_path),
                        k=K,
                    )
                except Exception as exc:
                    print(f"  VISUALIZATION ERROR for {sample_id}: {exc}")

                json_output_path = (
                    JSON_OUTPUT_DIR
                    / f"{safe_filename(strain)}_set{test_set_index}.json"
                )
                with open(json_output_path, "w") as jf:
                    json.dump(prediction_result, jf, indent=2)

                status = "KNOWN" if is_known else "unknown"
                correct_mark = ""
                if is_known and db_species:
                    pred = ranked[0]["species"] if ranked else ""
                    correct_mark = " OK" if pred == db_species else " WRONG"
                s0 = float(row["s0_score"]) if row["s0_score"] else 0.0
                print(
                    f"  [{status}]{correct_mark} {strain}/set{test_set_index} "
                    f"({len(raw_results)} segments, envs={','.join(sorted(set(environments)))}) "
                    f"-> {row['predicted_species']} (s0={s0:.4f})"
                )
                processed += 1

    print(f"\nDone. Processed: {processed}, Skipped (resume): {skipped}")
    print(f"Results saved to: {OUTPUT_CSV}")

    _draw_confusion_matrix(OUTPUT_CSV)
    return OUTPUT_CSV


def _draw_confusion_matrix(csv_path: Path) -> None:
    """Draw confusion matrix with unknown class from diverse retrieval results."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd
    from sklearn.metrics import confusion_matrix
    import seaborn as sns

    if not csv_path.exists():
        return
    df = pd.read_csv(csv_path)
    if df.empty:
        return

    y_true = []
    y_pred = []
    known_count = 0
    for _, row in df.iterrows():
        is_known = int(row.get("is_known", 1))
        correct_species = str(row.get("correct_species", ""))
        predicted = str(row.get("predicted_species", "unknown"))
        if is_known and correct_species:
            y_true.append(_strip_penicillium(correct_species))
            known_count += 1
        else:
            y_true.append("UNKNOWN")
        if not is_known:
            y_pred.append("UNKNOWN")
        elif correct_species and (
            predicted == correct_species
            or _strip_penicillium(predicted) == _strip_penicillium(correct_species)
        ):
            y_pred.append(_strip_penicillium(predicted))
        else:
            y_pred.append(_strip_penicillium(predicted))

    labels = sorted(set(y_true) | set(y_pred))
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    # Remove all-zero rows and columns
    row_sums = cm.sum(axis=1)
    col_sums = cm.sum(axis=0)
    import numpy as np

    keep = np.logical_or(row_sums > 0, col_sums > 0)
    keep_labels = [label for label, keep_label in zip(labels, keep) if keep_label]
    cm = cm[keep][:, keep]
    labels = keep_labels

    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp and yt != "UNKNOWN")

    accuracy = correct / max(known_count, 1)
    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="Blues",
        ax=ax,
    )
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(
        f"Threshold Retrieval Confusion Matrix\nAccuracy (known): {accuracy:.3f} | Known: {known_count}"
    )
    plt.xticks(rotation=90, fontsize=8)
    plt.yticks(rotation=0, fontsize=8)
    fig.tight_layout()
    out = OUTPUT_DIR / "confusion_matrix_threshold.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close()
    print(f"Confusion matrix saved to: {out}")
    print(f"  Known samples: {known_count}, Unknown samples: {len(df) - known_count}")
    print(f"  Accuracy (known only): {accuracy:.4f}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Retrieve diverse-data images against Qdrant and record scores."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max strains to process"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Skip already-processed IDs"
    )
    args = parser.parse_args()

    retrieve_diverse(limit=args.limit, resume=args.resume)


if __name__ == "__main__":
    main()
