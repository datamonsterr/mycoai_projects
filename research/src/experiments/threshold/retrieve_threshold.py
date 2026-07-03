"""
Retrieve threshold experiment: query Qdrant for threshold_retrieval_list.json entries.

Uses HIGHEST ACCURACY settings from program.md:
- Collection: myco_fungi_features_full_retrieval
- Extractor: EfficientNetB1_finetuned
- K: 11
- Environment strategy: E1 (same growth medium)
- Aggregation: weighted (score-weighted)
- Exclude self-matching via strain must_not filter

Output: results/threshold/diverse_retrieval_results.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import cv2  # noqa: E402

from src.config import (  # noqa: E402
    COLLECTION_NAME,
    QDRANT_API_KEY,
    QDRANT_URL,
    RESULTS_DIR,
    WORKSPACE_ROOT,
)
from src.experiments.feature_extraction.feature_extractors import (  # noqa: E402
    EfficientNetB1FinetunedExtractor,
)

_qdrant_url = QDRANT_URL
if not os.getenv("QDRANT_URL") or "cloud.qdrant" in _qdrant_url:
    _qdrant_url = "http://localhost:6333"

try:
    from qdrant_client import QdrantClient  # noqa: E402
    from qdrant_client.models import (  # noqa: E402
        FieldCondition,
        Filter,
        MatchValue,
    )
except ImportError:
    print("ERROR: qdrant_client not installed. Run: uv sync")
    sys.exit(1)

COLLECTION = f"{COLLECTION_NAME}_retrieval"
EXTRACTOR_KEY = "efficientnetb1_finetuned"
K = 11
TOP_N = 5

RETRIEVAL_LIST = RESULTS_DIR / "threshold" / "threshold_retrieval_list.json"
OUTPUT_CSV = RESULTS_DIR / "threshold" / "diverse_retrieval_results.csv"

CSV_FIELDS = (
    ["sample_id", "strain", "species_label", "is_known", "environment", "angle"]
    + [f"s{i}_score" for i in range(TOP_N)]
    + [f"s{i}_species" for i in range(TOP_N)]
    + ["predicted_species", "predicted_confidence", "image_path"]
)


def aggregate_weighted(neighbors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    totals: Dict[str, float] = {}
    for n in neighbors:
        sp = n.get("specy") or n.get("species", "unknown")
        score = float(n.get("score", 0.0))
        totals[sp] = totals.get(sp, 0.0) + score
    total_weight = sum(totals.values()) or 1.0
    return sorted(
        [{"species": sp, "score": s / total_weight} for sp, s in totals.items()],
        key=lambda x: x["score"],
        reverse=True,
    )


def load_done_ids(csv_path: Path) -> set:
    if not csv_path.exists():
        return set()
    with open(csv_path, newline="") as f:
        return {row["sample_id"] for row in csv.DictReader(f)}


def run_retrieval(resume: bool = False, limit: Optional[int] = None) -> Path:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    with open(RETRIEVAL_LIST) as f:
        retrieval_list = json.load(f)
    print(f"Loaded {len(retrieval_list)} entries from retrieval list")

    done_ids = load_done_ids(OUTPUT_CSV) if resume else set()
    if resume and done_ids:
        print(f"Resuming: {len(done_ids)} already processed, skipping")

    client = QdrantClient(url=_qdrant_url, api_key=QDRANT_API_KEY, timeout=30)
    try:
        info = client.get_collection(COLLECTION)
        print(f"Qdrant collection '{COLLECTION}': {info.points_count} points")
    except Exception as e:
        print(f"ERROR accessing Qdrant collection '{COLLECTION}': {e}")
        print("Run: docker compose up -d  (and ensure collection is populated)")
        sys.exit(1)

    extractor = EfficientNetB1FinetunedExtractor()

    mode = "a" if resume and OUTPUT_CSV.exists() else "w"
    image_failures = 0
    qdrant_failures = 0
    processed = 0
    skipped = 0

    with open(OUTPUT_CSV, mode, newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
        if mode == "w":
            writer.writeheader()

        for idx, entry in enumerate(retrieval_list):
            if limit and processed >= limit:
                break

            sample_id = entry["sample_id"]
            if resume and sample_id in done_ids:
                skipped += 1
                continue

            strain = entry.get("strain", "")
            species_label = entry.get("species", "")
            is_known = entry.get("is_known", False)
            environment = entry.get("environment", "unknown")
            angle = entry.get("angle", "unknown")
            image_path_rel = entry.get("image_path", "")

            if not image_path_rel:
                print(f"  SKIP {sample_id}: no image_path")
                image_failures += 1
                continue

            img_path = WORKSPACE_ROOT / image_path_rel
            if not img_path.exists():
                print(f"  SKIP {sample_id}: image not found: {img_path}")
                image_failures += 1
                continue

            img_bgr = cv2.imread(str(img_path))
            if img_bgr is None:
                print(f"  SKIP {sample_id}: cannot read image")
                image_failures += 1
                continue

            try:
                features = extractor.extract(img_bgr)
            except Exception as exc:
                print(f"  SKIP {sample_id}: feature extraction failed: {exc}")
                image_failures += 1
                continue

            env_filter = Filter(
                must_not=[
                    FieldCondition(key="strain", match=MatchValue(value=strain))
                ]
            )
            if environment.lower() not in ("unknown", ""):
                env_filter = Filter(
                    must=[
                        FieldCondition(
                            key="environment", match=MatchValue(value=environment.upper())
                        )
                    ],
                    must_not=[
                        FieldCondition(key="strain", match=MatchValue(value=strain))
                    ],
                )

            try:
                results = client.query_points(
                    collection_name=COLLECTION,
                    query=features.tolist(),
                    using=EXTRACTOR_KEY,
                    query_filter=env_filter,
                    limit=K,
                    with_payload=True,
                )
            except Exception as exc:
                print(f"  SKIP {sample_id}: Qdrant query failed: {exc}")
                qdrant_failures += 1
                continue

            neighbors = []
            for hit in results.points:
                payload = hit.payload or {}
                neighbors.append(
                    {
                        "specy": payload.get("specy", "unknown"),
                        "score": hit.score,
                        "strain": payload.get("strain", ""),
                        "environment": payload.get("environment", ""),
                    }
                )

            ranked = aggregate_weighted(neighbors) if neighbors else []

            top_species = ranked[0]["species"] if ranked else "unknown"
            top_confidence = ranked[0]["score"] if ranked else 0.0

            row: Dict[str, Any] = {
                "sample_id": sample_id,
                "strain": strain,
                "species_label": species_label,
                "is_known": int(is_known),
                "environment": environment,
                "angle": angle,
                "predicted_species": top_species,
                "predicted_confidence": f"{top_confidence:.6f}",
                "image_path": str(image_path_rel),
            }
            for i in range(TOP_N):
                if i < len(ranked):
                    row[f"s{i}_score"] = f"{ranked[i]['score']:.6f}"
                    row[f"s{i}_species"] = ranked[i]["species"]
                else:
                    row[f"s{i}_score"] = ""
                    row[f"s{i}_species"] = ""

            writer.writerow(row)
            csvfile.flush()
            processed += 1

            if processed % 50 == 0:
                known_so_far = sum(
                    1
                    for _ in range(max(0, processed - 50), processed)
                )
                print(
                    f"  [{processed}/{len(retrieval_list)}] {sample_id} "
                    f"-> {top_species} (conf={top_confidence:.4f}, "
                    f"neighbors={len(neighbors)})"
                )
            elif processed <= 5:
                print(
                    f"  [{processed}/{len(retrieval_list)}] {sample_id} "
                    f"-> {top_species} (conf={top_confidence:.4f}, "
                    f"neighbors={len(neighbors)})"
                )

    print(f"\nDone. Processed: {processed}, Skipped (resume): {skipped}")
    print(f"Image failures: {image_failures}, Qdrant failures: {qdrant_failures}")
    print(f"Results saved to: {OUTPUT_CSV}")
    return OUTPUT_CSV


def main():
    parser = argparse.ArgumentParser(
        description="Retrieve threshold experiment: query Qdrant for retrieval list"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Skip already-processed sample_ids"
    )
    parser.add_argument("--limit", type=int, default=None, help="Max entries to process")
    args = parser.parse_args()
    run_retrieval(resume=args.resume, limit=args.limit)


if __name__ == "__main__":
    main()
