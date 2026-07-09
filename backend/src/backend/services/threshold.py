"""Threshold formulas for known/unknown species confidence scoring.

Ported from research/src/experiments/threshold/threshold_analysis.py

Given top-k neighbor scores (s0, s1, ..., s{k-1}), apply formula formulas
to produce a single confidence score. The confidence score can be used with
a pre-computed threshold to flag potential unknown species.

Latest regenerated threshold benchmark: gap_0_2 / gap02_sq family with roc_opt threshold
  Best F1 = 0.3409 on 48 known vs 294 unknown grouped test sets.

Backend currently keeps gnorm_0_2 as product default for UI stability until
research-best formula is explicitly promoted into application behavior.
"""

from __future__ import annotations

import math
from collections.abc import Callable

# Top formulas from expanded threshold analysis (sorted by f1_grid F1)
# Source: research/results/threshold/all_experiments.csv
FORMULAS: dict[str, Callable[..., float]] = {}


def _register(name: str) -> Callable:
    def decorator(fn):
        FORMULAS[name] = fn
        return fn

    return decorator


@_register("s0")
def _s0(scores: list[float]) -> float:
    return scores[0] if len(scores) > 0 else 0.0


@_register("abs_gap")
def _abs_gap(scores: list[float]) -> float:
    return scores[0] - scores[1] if len(scores) >= 2 else 0.0


@_register("gap_norm")
def _gap_norm(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.0
    return (scores[0] - scores[1]) / (scores[0] + scores[1] + 1e-12)


@_register("gnorm_0_2")
def _gnorm_0_2(scores: list[float]) -> float:
    if len(scores) < 3:
        return 0.0
    return (scores[0] - scores[2]) / (scores[0] + scores[2] + 1e-12)


@_register("ratio_s0s1")
def _ratio_s0s1(scores: list[float]) -> float:
    if len(scores) < 2 or scores[1] < 1e-12:
        return 1.0
    return scores[0] / (scores[1] + 1e-12)


@_register("top2_avg")
def _top2_avg(scores: list[float]) -> float:
    top = sorted(scores, reverse=True)[:2]
    return sum(top) / max(len(top), 1)


@_register("top3_avg")
def _top3_avg(scores: list[float]) -> float:
    top = sorted(scores, reverse=True)[:3]
    return sum(top) / max(len(top), 1)


@_register("product_s0s1")
def _product_s0s1(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.0
    return scores[0] * scores[1]


@_register("neg_entropy")
def _neg_entropy(scores: list[float]) -> float:
    top = [max(s, 1e-12) for s in scores[:5]]
    row_sum = sum(top) + 1e-12
    p = [s / row_sum for s in top]
    entropy = -sum(pi * math.log(pi) for pi in p if pi > 0)
    max_entropy = math.log(max(len(top), 1))
    return 1.0 - entropy / (max_entropy + 1e-12)


@_register("geom_mean_top3")
def _geom_mean_top3(scores: list[float]) -> float:
    top = sorted(scores, reverse=True)[:3]
    if not top:
        return 0.0
    prod = 1.0
    for s in top:
        prod *= max(s, 1e-12)
    return prod ** (1.0 / len(top))


@_register("weighted_sum_exp")
def _weighted_sum_exp(scores: list[float]) -> float:
    w = [1.0, 0.5, 0.25, 0.125, 0.0625]
    return sum(scores[i] * w[i] for i in range(min(len(scores), len(w))))


@_register("std_top3")
def _std_top3(scores: list[float]) -> float:
    top = scores[:3]
    if len(top) < 2:
        return 0.0
    mean = sum(top) / len(top)
    var = sum((s - mean) ** 2 for s in top) / len(top)
    return math.sqrt(var)


def compute_confidence(
    scores: list[float],
    formula: str = "gnorm_0_2",
) -> float:
    """Compute threshold confidence score from neighbor similarity scores.

    Args:
        scores: Top-k neighbor similarity scores (sorted descending).
        formula: Formula name from FORMULAS dict.

    Returns:
        Confidence score in [0, 1] or beyond for ratio-based formulas.
    """
    fn = FORMULAS.get(formula)
    if fn is None:
        return 0.0
    try:
        return float(fn(scores))
    except (ValueError, ZeroDivisionError):
        return 0.0


# Threshold defaults pinned from latest regenerated threshold artifacts.
# Note: research-best currently belongs to gap_0_2 / gap02_sq family with
# roc_opt threshold ~= 0.005904, but backend still serves gnorm_0_2 by default.
OPTIMAL_THRESHOLDS: dict[str, float] = {
    "gnorm_0_2": 0.12,
    "abs_gap": 0.09,
    "gap_norm": 0.40,
    "ratio_s0s1": 1.35,
    "top2_avg": 0.22,
    "top3_avg": 0.19,
    "neg_entropy": 0.15,
    "weighted_sum_exp": 0.14,
    "s0": 0.18,
}


def is_known_confidence(
    scores: list[float],
    formula: str = "gnorm_0_2",
    threshold: float | None = None,
) -> dict[str, float | bool]:
    """Compute formula-based confidence and classify as known/unknown.

    Returns dict with:
        confidence: raw formula score
        threshold: threshold used
        is_known: True if confidence >= threshold
        formula: formula name used
    """
    confidence = compute_confidence(scores, formula)
    if threshold is None:
        threshold = OPTIMAL_THRESHOLDS.get(formula, 0.1)
    return {
        "confidence": round(confidence, 6),
        "threshold": round(threshold, 6),
        "is_known": confidence >= threshold,
        "formula": formula,
    }
