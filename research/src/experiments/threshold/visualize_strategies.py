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
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

import numpy as np
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RESULTS_DIR, WORKSPACE_ROOT  # noqa: E402

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
    rows = []
    labels = []
    scores_mat = []

    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            labels.append(int(row.get("is_known", 0)))
            row_scores = []
            for i in range(5):
                val = row.get(f"s{i}_score", "")
                row_scores.append(float(val) if val else 0.0)
            scores_mat.append(row_scores)

    labels_arr = np.array(labels, dtype=float)
    scores_arr = np.array(scores_mat, dtype=float)
    return rows, labels_arr, scores_arr


def compute_strategy_scores(scores_arr: np.ndarray, formula_name: str) -> np.ndarray:
    """Re-compute scores for a specific formula using the same logic as expanded_threshold_analysis."""
    # This requires duplicating generate_formulas logic or loading from CSV.
    # Given the complexity, I will load from the results CSV which already has the scores.
    pass

def load_results(csv_path: Path) -> Tuple[List[Dict[str, Any]], np.ndarray, np.ndarray]:
    rows = []
    labels = []
    scores_mat = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
            labels.append(int(row.get("is_known", 0)))
            row_scores = [float(row.get(f"s{i}_score", "") or 0.0) for i in range(5)]
            scores_mat.append(row_scores)
    
    return rows, np.array(labels, dtype=float), np.array(scores_mat, dtype=float)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formula", type=str, default="gm_top2")
    parser.add_argument("--threshold", type=float, default=0.156562)
    args = parser.parse_args()

    # I need to compute the formula value for each sample.
    # The simplest way is to re-run the formula logic here.
    # But for now, I will just hardcode the logic for 'gm_top2' and others I need.
    pass

