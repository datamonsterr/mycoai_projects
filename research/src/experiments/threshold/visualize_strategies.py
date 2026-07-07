"""
Per-strategy visualization for threshold experiment.

For each strategy × algorithm combination, creates a folder with:
  - A grid image showing samples grouped by TP / FP / TN / FN
  - Each cell: thumbnail + (is_known?, predicted, actual, score)

Usage:
    uv run python -m src.experiments.threshold.visualize_strategies
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RESULTS_DIR  # noqa: E402

INPUT_CSV = RESULTS_DIR / "threshold" / "diverse_retrieval_results.csv"
OUTPUT_DIR = RESULTS_DIR / "threshold" / "strategy_visualizations"


# ---------------------------------------------------------------------------
# Load retrieval data
# ---------------------------------------------------------------------------


def load_results(
    csv_path: Path,
) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    """
    Returns:
        rows       : list of dicts (CSV rows)
        labels     : (N,) 1=known, 0=unknown
        scores_arr : (N, 5) s0..s4 scores
    """
    rows: List[Dict[str, Any]] = []
    labels: List[int] = []
    scores_mat: List[List[float]] = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            labels.append(int(row.get("is_known", 0)))
            row_scores = [float(row.get(f"s{i}_score", "") or 0.0) for i in range(5)]
            scores_mat.append(row_scores)

    labels_arr = np.array(labels, dtype=float)
    scores_arr = np.array(scores_mat, dtype=float)
    return rows, labels_arr, scores_arr


def main() -> None:
    print(f"Strategy visualization tool. Input: {INPUT_CSV}")
    print(f"Output dir: {OUTPUT_DIR}")
