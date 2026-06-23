"""
Structured experiment results analysis.

Creates per-experiment folders with:
  - correct/ and incorrect/ visualization copies
  - confusion_matrix.png (species-level, all test sets counted)
  - analytics.json (well-defined metrics)
  - analytics.csv (tabular format)
  - per_species_accuracy.png (bar chart)
  - per_fold_accuracy.png (fold comparison)

Usage:
  uv run python -m src.analysis.experiment_analysis --csv results/cv_results.csv
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config import RESULTS_DIR


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class ExperimentConfig:
    extractor: str
    media_strategy: str
    agg_strategy: str
    k: int
    collection: str

    @property
    def folder_name(self) -> str:
        return f"{self.extractor}_{self.media_strategy}_{self.agg_strategy}_k{self.k}"


@dataclass
class PerSpeciesMetrics:
    species: str
    total: int = 0
    correct: int = 0
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0


@dataclass
class ExperimentAnalytics:
    config: ExperimentConfig
    n_predictions: int = 0
    n_correct: int = 0
    mean_accuracy: float = 0.0
    std_accuracy: float = 0.0
    n_folds: int = 0
    n_species: int = 0
    per_species: List[PerSpeciesMetrics] = field(default_factory=list)
    per_fold: Dict[int, float] = field(default_factory=dict)
    confusion_counts: Dict[str, Dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------


def draw_confusion_matrix(
    predictions: List[Dict[str, Any]],
    output_path: str,
    title: str = "",
    figsize: Tuple[int, int] = (14, 10),
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    from sklearn.metrics import confusion_matrix as sk_confusion

    y_true = [p["ground_truth"] for p in predictions]
    y_pred = [p["predicted_specy"] for p in predictions]

    correct_count = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = (correct_count / len(predictions) * 100.0) if predictions else 0.0

    labels = sorted(set(y_true) | set(y_pred))
    cm = sk_confusion(y_true, y_pred, labels=labels)

    plt.figure(figsize=figsize)
    ax = sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="Blues",
        cbar_kws={"label": "Count"},
    )
    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    display_title = title or f"Confusion Matrix — {accuracy:.1f}% ({correct_count}/{len(predictions)} predictions)"
    ax.set_title(display_title, fontsize=14, fontweight="bold")
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def draw_per_species_accuracy(
    per_species: List[PerSpeciesMetrics],
    output_path: str,
    title: str = "",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    species_list = [m.species for m in per_species]
    accuracies = [m.accuracy for m in per_species]
    counts = [m.total for m in per_species]

    colors = ["#2ecc71" if a >= 0.5 else "#e74c3c" for a in accuracies]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(range(len(species_list)), accuracies, color=colors, edgecolor="white")

    for i, (bar, acc, n) in enumerate(zip(bars, accuracies, counts)):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{acc:.1%}\n({n})",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    ax.set_xticks(range(len(species_list)))
    ax.set_xticklabels([s.replace("Penicillium ", "P. ") for s in species_list],
                       rotation=45, ha="right", fontsize=10)
    ax.set_ylabel("Accuracy", fontsize=12)
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.3)
    display_title = title or "Per-Species Accuracy"
    ax.set_title(display_title, fontsize=14, fontweight="bold")
    ax.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def draw_per_fold_accuracy(
    per_fold: Dict[int, float],
    output_path: str,
    title: str = "",
) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    folds = sorted(per_fold.keys())
    accuracies = [per_fold[f] for f in folds]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(folds, accuracies, "o-", color="#3498db", linewidth=2, markersize=10,
            markerfacecolor="white", markeredgewidth=2)

    for f, a in zip(folds, accuracies):
        ax.annotate(f"{a:.1%}", (f, a), textcoords="offset points",
                    xytext=(0, 12), ha="center", fontsize=10, fontweight="bold")

    mean_acc = np.mean(accuracies)
    ax.axhline(y=mean_acc, color="#e74c3c", linestyle="--", alpha=0.5,
               label=f"Mean: {mean_acc:.1%}")

    ax.set_xticks(folds)
    ax.set_xlabel("Fold", fontsize=12)
    ax.set_ylabel("Accuracy", fontsize=12)
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=10)
    display_title = title or "Per-Fold Accuracy"
    ax.set_title(display_title, fontsize=14, fontweight="bold")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------


def compute_experiment_analytics(
    df: pd.DataFrame,
    config: ExperimentConfig,
) -> ExperimentAnalytics:
    exp_df = df[
        (df["extractor"] == config.extractor)
        & (df["media_strategy"] == config.media_strategy)
        & (df["agg_strategy"] == config.agg_strategy)
        & (df["k"] == config.k)
    ]
    if exp_df.empty:
        return ExperimentAnalytics(config=config)

    analytics = ExperimentAnalytics(
        config=config,
        n_predictions=len(exp_df),
        n_correct=int(exp_df["correct"].sum()),
        mean_accuracy=float(exp_df["correct"].mean()),
        std_accuracy=float(exp_df.groupby("fold")["correct"].mean().std()),
        n_folds=exp_df["fold"].nunique(),
        n_species=exp_df["species"].nunique(),
    )

    for fid, grp in exp_df.groupby("fold"):
        analytics.per_fold[int(fid)] = float(grp["correct"].mean())

    all_species = sorted(set(exp_df["ground_truth"].unique()) | set(exp_df["predicted_specy"].unique()))

    for sp in sorted(exp_df["species"].unique()):
        sp_rows = exp_df[exp_df["species"] == sp]
        tp = int(sp_rows["correct"].sum())
        total = len(sp_rows)
        fp = int(((exp_df["predicted_specy"] == sp) & (exp_df["ground_truth"] != sp)).sum())
        fn = int(((exp_df["ground_truth"] == sp) & (exp_df["predicted_specy"] != sp)).sum())

        accuracy = tp / total if total > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        analytics.per_species.append(PerSpeciesMetrics(
            species=sp, total=total, correct=tp,
            accuracy=accuracy, precision=precision, recall=recall, f1=f1,
        ))

    confusion: Dict[str, Dict[str, int]] = {sp: {s: 0 for s in all_species} for sp in all_species}
    for _, row in exp_df.iterrows():
        gt = row["ground_truth"]
        pred = row["predicted_specy"]
        confusion[gt][pred] = confusion.get(gt, {}).get(pred, 0) + 1
    analytics.confusion_counts = confusion

    return analytics


# ---------------------------------------------------------------------------
# Folder builder
# ---------------------------------------------------------------------------


def build_experiment_results_folder(
    df: pd.DataFrame,
    config: ExperimentConfig,
    output_root: Path,
    source_vis_dir: Optional[Path] = None,
) -> Path:
    exp_dir = output_root / config.folder_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    analytics = compute_experiment_analytics(df, config)

    correct_dir = exp_dir / "correct"
    incorrect_dir = exp_dir / "incorrect"
    correct_dir.mkdir(exist_ok=True)
    incorrect_dir.mkdir(exist_ok=True)

    exp_df = df[
        (df["extractor"] == config.extractor)
        & (df["media_strategy"] == config.media_strategy)
        & (df["agg_strategy"] == config.agg_strategy)
        & (df["k"] == config.k)
    ]

    predictions: List[Dict[str, Any]] = []
    for _, row in exp_df.iterrows():
        pred = {
            "ground_truth": row["ground_truth"],
            "predicted_specy": row["predicted_specy"],
            "correct": bool(row["correct"]),
            "strain": row["strain"],
            "fold": int(row["fold"]),
            "test_set_index": int(row["test_set_index"]),
            "species": row["species"],
        }
        predictions.append(pred)

    if source_vis_dir and source_vis_dir.exists():
        for vis_file in sorted(source_vis_dir.glob("pred_*.jpg")):
            strain_name = vis_file.stem.replace("pred_", "")
            is_correct = any(
                p["correct"] for p in predictions
                if p["strain"] == strain_name.split("_set")[0]
                and f"set{p['test_set_index']}" == strain_name.split("_set")[-1]
                if "_set" in strain_name
            )
            target = (correct_dir if is_correct else incorrect_dir) / vis_file.name
            if not target.exists():
                shutil.copy2(vis_file, target)

    draw_confusion_matrix(
        predictions,
        str(exp_dir / "confusion_matrix.png"),
        title=f"{config.folder_name} — {analytics.mean_accuracy:.1%}",
    )

    draw_per_species_accuracy(
        analytics.per_species,
        str(exp_dir / "per_species_accuracy.png"),
        title=f"{config.folder_name} — Per-Species Accuracy",
    )

    draw_per_fold_accuracy(
        analytics.per_fold,
        str(exp_dir / "per_fold_accuracy.png"),
        title=f"{config.folder_name} — Per-Fold Accuracy",
    )

    results_csv = exp_dir / "results.csv"
    exp_df.to_csv(results_csv, index=False)

    analytics_json = {
        "config": {
            "extractor": config.extractor,
            "media_strategy": config.media_strategy,
            "agg_strategy": config.agg_strategy,
            "k": config.k,
            "collection": config.collection,
        },
        "summary": {
            "n_predictions": analytics.n_predictions,
            "n_correct": analytics.n_correct,
            "mean_accuracy": analytics.mean_accuracy,
            "std_accuracy": analytics.std_accuracy,
            "n_folds": analytics.n_folds,
            "n_species": analytics.n_species,
        },
        "per_species": [asdict(m) for m in analytics.per_species],
        "per_fold": analytics.per_fold,
        "confusion_matrix": analytics.confusion_counts,
    }
    with open(exp_dir / "analytics.json", "w") as f:
        json.dump(analytics_json, f, indent=2)

    analytics_df = pd.DataFrame([asdict(m) for m in analytics.per_species])
    if not analytics_df.empty:
        analytics_df = analytics_df.sort_values("f1", ascending=False)
        analytics_df.to_csv(exp_dir / "per_species_analytics.csv", index=False)

    return exp_dir


# ---------------------------------------------------------------------------
# Main: discover configs from CSV and build all folders
# ---------------------------------------------------------------------------


def build_all_results(
    csv_path: Path,
    output_root: Path | None = None,
    source_vis_root: Path | None = None,
) -> List[Path]:
    df = pd.read_csv(csv_path)
    if df.empty:
        print("Empty CSV, nothing to do.")
        return []

    if "media_strategy" not in df.columns:
        if "env_strategy" in df.columns:
            df["media_strategy"] = df["env_strategy"]
        else:
            df["media_strategy"] = ""

    output_root = output_root or (RESULTS_DIR / "experiment_analysis")
    output_root.mkdir(parents=True, exist_ok=True)

    configs: set[Tuple[str, str, str, int, str]] = set()
    for _, row in df.iterrows():
        media_col = row.get("media_strategy", row.get("env_strategy", ""))
        configs.add((
            row["extractor"],
            media_col,
            row["agg_strategy"],
            int(row["k"]),
            row.get("collection", ""),
        ))

    results: List[Path] = []
    for extractor, media, agg, k, coll in sorted(configs):
        config = ExperimentConfig(
            extractor=extractor,
            media_strategy=media,
            agg_strategy=agg,
            k=k,
            collection=coll,
        )
        print(f"Building: {config.folder_name} ...", flush=True)
        vis_dir = None
        if source_vis_root:
            df_config = df[
                (df["extractor"] == extractor)
                & (df.get("media_strategy", df["env_strategy"]) == media)
                & (df["agg_strategy"] == agg)
                & (df["k"] == k)
            ]
            if not df_config.empty:
                sample_fold = int(df_config["fold"].iloc[0])
                vis_candidate = (
                    source_vis_root
                    / f"fold{sample_fold}_{media}_{agg}_k{k}"
                    / "visualizations"
                )
                if vis_candidate.exists():
                    vis_dir = vis_candidate

        exp_dir = build_experiment_results_folder(
            df, config, output_root, source_vis_dir=vis_dir,
        )
        results.append(exp_dir)
        print(f"  -> {exp_dir}", flush=True)

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Build structured experiment results")
    parser.add_argument("--csv", required=True, help="Path to CV results CSV")
    parser.add_argument("--output", default=None, help="Output root directory")
    parser.add_argument("--vis-root", default=None, help="Root for finding visualization sources")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return

    output_root = Path(args.output) if args.output else None
    vis_root = Path(args.vis_root) if args.vis_root else None

    results = build_all_results(csv_path, output_root, vis_root)
    print(f"\nBuilt {len(results)} experiment folders")


if __name__ == "__main__":
    main()
