"""
Refitted threshold retrieval: fresh-query fold0 held-out strains vs rest.

Usage:
    uv run python -m src.experiments.threshold.retrieve_refitted
    uv run python -m src.experiments.threshold.retrieve_refitted --limit 50
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import cv2
from qdrant_client import QdrantClient

import pandas as pd

from src.config import DATASET_ROOT, QDRANT_API_KEY, QDRANT_URL, RESULTS_DIR, STRAIN_SPECIES_MAPPING_PATH
from src.utils.qdrant_query import build_filter, get_image_features

# Override to local Docker Qdrant when QDRANT_URL not set
import os
_qdrant_url = QDRANT_URL
if os.getenv("QDRANT_URL", None) == QDRANT_URL:
    _qdrant_url = QDRANT_URL
if not os.getenv("QDRANT_URL"):
    _qdrant_url = "http://127.0.0.1:6333"

COLLECTION = "qdrant-research"
EXTRACTOR_KEY = "resnet50"
K = 11
TOP_N = 5
OUTPUT_DIR = RESULTS_DIR / "threshold"
OUTPUT_CSV = OUTPUT_DIR / "diverse_retrieval_results.csv"
FOLDS_DIR = DATASET_ROOT / "folds"
PREPARED_SEGMENTS_PATH = DATASET_ROOT / "prepared_segments_metadata.json"

CSV_FIELDS = (
    ["sample_id", "strain", "test_set_index", "species_label", "is_known", "environment", "angle"]
    + [f"s{i}_score" for i in range(TOP_N)]
    + [f"s{i}_species" for i in range(TOP_N)]
    + ["predicted_species", "correct_species", "image_path"]
)


def _load_payload() -> tuple[dict[str, Any], dict[str, Any]]:
    if not PREPARED_SEGMENTS_PATH.exists():
        raise FileNotFoundError(f"Prepared segments metadata not found: {PREPARED_SEGMENTS_PATH}")
    rows = json.loads(PREPARED_SEGMENTS_PATH.read_text())
    lookup: dict[str, dict[str, Any]] = {r["id"]: r for r in rows if r.get("id")}
    by_strain: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        strain = (r.get("data", {}) or {}).get("strain")
        if strain:
            by_strain.setdefault(strain, []).append(r)
    return lookup, by_strain


def _build_test_sets(
    held_out_strains: set[str],
    lookup: dict[str, Any],
    by_strain: dict[str, list],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for strain in held_out_strains:
        rows = by_strain.get(strain, [])
        if not rows:
            continue
        # Build a test set using all segments for the strain
        group: list[dict[str, Any]] = []
        environments: list[str] = []
        for row in rows:
            data = row.get("data", {}) or {}
            segment_path = row.get("segment_path")
            if not segment_path:
                continue
            image_path = str(DATASET_ROOT.parent / segment_path)
            if not Path(image_path).exists():
                continue
            env = data.get("environment", "unknown")
            group.append({
                "image_id": row["id"],
                "image_path": image_path,
                "environment": env,
                "angle": data.get("angle", "unknown"),
            })
            if env not in environments:
                environments.append(env)
        if group:
            # Keep original test_set_index flow: one group per strain = 0
            result.append({
                "strain": strain,
                "species_label": rows[0].get("data", {}).get("species") or rows[0].get("data", {}).get("specy") or "unknown",
                "is_known": 1,
                "environment": ",".join(sorted(set(environments))),
                "angle": ",".join(sorted({d.get("angle", "unknown") for d in group})),
                "sample_id": f"{strain}__set0",
                "test_set_index": 0,
                "group": group,
            })
    return result


def _is_species_known(species_label: str, known_species: set[str]) -> bool:
    """Check if a species label matches a known database species.
    
    Normalises by stripping 'Penicillium ' prefix from both sides
    and comparing case-insensitively.
    """
    if not species_label or species_label.lower() == "unknown":
        return False
    label_norm = species_label.strip()
    if label_norm.lower().startswith("penicillium "):
        label_norm = label_norm[len("penicillium "):]
    for ks in known_species:
        ks_norm = ks.strip()
        if ks_norm.lower().startswith("penicillium "):
            ks_norm = ks_norm[len("penicillium "):]
        if label_norm.lower() == ks_norm.lower():
            return True
    return False


def _build_unknown_test_sets(
    lookup: dict[str, Any],
    by_strain: dict[str, list],
    exclude_strains: set[str],
    known_species: set[str],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for strain, rows in by_strain.items():
        if strain in exclude_strains:
            continue
        data0 = (rows[0].get("data", {}) or {}) if rows else {}
        species_label = data0.get("species") or data0.get("specy") or "unknown"
        group: list[dict[str, Any]] = []
        environments: list[str] = []
        for row in rows:
            data = row.get("data", {}) or {}
            segment_path = row.get("segment_path")
            if not segment_path:
                continue
            image_path = str(DATASET_ROOT.parent / segment_path)
            if not Path(image_path).exists():
                continue
            env = data.get("environment", "unknown")
            group.append({
                "image_id": row["id"],
                "image_path": image_path,
                "environment": env,
                "angle": data.get("angle", "unknown"),
            })
            if env not in environments:
                environments.append(env)
        if group:
            is_known = 1 if _is_species_known(species_label, known_species) else 0
            result.append({
                "strain": strain,
                "species_label": species_label,
                "is_known": is_known,
                "environment": ",".join(sorted(set(environments))),
                "angle": ",".join(sorted({d.get("angle", "unknown") for d in group})),
                "sample_id": f"{strain}__set0",
                "test_set_index": 0,
                "group": group,
            })
    return result


def _get_held_out_strains(fold: int = 0) -> set[str]:
    strains: set[str] = set()
    for path in sorted(FOLDS_DIR.glob(f"fold_{fold}_*.json")):
        data = json.loads(path.read_text())
        strains.add(data["test_strain"])
    return strains


def _extract_features_once(image_path: str) -> list[float] | None:
    from src.experiments.feature_extraction.feature_extractors import ResNet50Extractor
    _extractor = ResNet50Extractor()
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        features = _extractor.extract(img)
        return features.tolist()
    except Exception:
        return None


def _query_qdrant_for_set(
    client: QdrantClient,
    test_set: dict[str, Any],
    exclude_strain: str,
) -> list[dict[str, Any]]:
    """Query Qdrant for one test-set group, aggregate, and return a CSV-ready row."""
    all_neighbors: list[dict[str, Any]] = []
    for seg in test_set["group"]:
        features = _extract_features_once(seg["image_path"])
        if features is None:
            continue
        search_filter = build_filter(
            environment=seg.get("environment"),
            exclude_strain=exclude_strain,
        )
        try:
            response = client.query_points(
                collection_name=COLLECTION,
                query=features,
                using=EXTRACTOR_KEY,
                query_filter=search_filter,
                limit=K,
                with_payload=True,
            )
            for point in response.points:
                payload = point.payload or {}
                all_neighbors.append({
                    "specy": payload.get("specy") or payload.get("species", "unknown"),
                    "score": point.score,
                    "strain": payload.get("strain", ""),
                    "environment": payload.get("environment", ""),
                })
        except Exception:
            continue

    if not all_neighbors:
        return []
    all_neighbors.sort(key=lambda n: float(n["score"]), reverse=True)
    top = all_neighbors[:TOP_N]
    # aggregate
    totals: dict[str, float] = {}
    for n in all_neighbors:
        sp = n.get("specy", "unknown")
        totals[sp] = totals.get(sp, 0.0) + float(n.get("score", 0.0))
    total_weight = sum(totals.values()) or 1.0
    ranked = sorted(
        [{"species": sp, "score": s / total_weight} for sp, s in totals.items()],
        key=lambda x: x["score"],
        reverse=True,
    )
    row: dict[str, Any] = {
        "sample_id": test_set["sample_id"],
        "strain": test_set["strain"],
        "test_set_index": test_set["test_set_index"],
        "species_label": test_set["species_label"],
        "is_known": test_set["is_known"],
        "environment": test_set["environment"],
        "angle": test_set["angle"],
        "predicted_species": ranked[0]["species"] if ranked else "unknown",
        "correct_species": test_set["species_label"] if test_set["is_known"] else "",
        "image_path": ";".join(s["image_path"] for s in test_set["group"]),
    }
    for i in range(TOP_N):
        if i < len(ranked):
            row[f"s{i}_score"] = f"{ranked[i]['score']:.6f}"
            row[f"s{i}_species"] = ranked[i]["species"]
        else:
            row[f"s{i}_score"] = ""
            row[f"s{i}_species"] = ""
    return [row]


def main() -> None:
    parser = argparse.ArgumentParser(description="Refitted threshold retrieval")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--fold", type=int, default=0)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    lookup, by_strain = _load_payload()

    # Collect known species from strain-species mapping
    known_species: set[str] = set()
    if STRAIN_SPECIES_MAPPING_PATH.exists():
        df_map = pd.read_csv(STRAIN_SPECIES_MAPPING_PATH)
        known_species = set(df_map["Species"].dropna().astype(str))

    held_out = _get_held_out_strains(args.fold)
    print(f"Held-out strains (fold {args.fold}):", sorted(held_out))
    known_sets = _build_test_sets(held_out, lookup, by_strain)
    print(f"Known test sets: {len(known_sets)}")
    unknown_sets = _build_unknown_test_sets(lookup, by_strain, held_out, known_species)
    print(f"Unknown test sets: {len(unknown_sets)}")
    all_sets = known_sets + unknown_sets
    if args.limit:
        all_sets = all_sets[:args.limit]
    print(f"Total sets to retrieve: {len(all_sets)}")

    client = QdrantClient(url=_qdrant_url, api_key=QDRANT_API_KEY or None, timeout=120)
    mode = "w"
    processed = 0
    with open(OUTPUT_CSV, mode, newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        if mode == "w":
            writer.writeheader()
        for test_set in all_sets:
            rows = _query_qdrant_for_set(client, test_set, test_set["strain"])
            for row in rows:
                writer.writerow(row)
            processed += 1
            status = "KNOWN" if test_set["is_known"] else "UNK"
            s0 = rows[0].get("s0_score", "") if rows else ""
            print(f"[{status}] {test_set['strain']} s0={s0}")
        csvfile.flush()
    print(f"\nDone. Processed {processed} sets.")
    print(f"Results: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
