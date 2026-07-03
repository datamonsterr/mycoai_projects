"""Comprehensive retrieval experiment charts for the graduation report.

Generates:
  1. Bar chart: Top-15 highest accuracy configs (yolo)
  2. Bar chart: KMeans vs YOLO comparison (specific configs)
  3. Heatmaps: K × Media, K × Agg, Agg × Media (best extractors)
  4. Hyperparameter stats table (min/mean/max per hyperparam)
  5. Sample prediction visualizations

Uses existing evaluation results from results/retrieval_*/
and runs missing (focused) configs as needed.
"""
from __future__ import annotations

import json
import re
import sys
import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT = Path("/home/dat/dev/mycoai")
LATEX_FIGURES = PROJECT / "graduation_report/figures"
REPORT_FIGURES = PROJECT / "graduation_report/report/figures"
CODE_DIR = PROJECT / "graduation_report/code"
RESULTS_DIR = PROJECT / "results"
LATEX_FIGURES.mkdir(parents=True, exist_ok=True)
REPORT_FIGURES.mkdir(parents=True, exist_ok=True)

STYLE = {
    "font.family": "serif",
    "font.size": 12,
    "axes.titlesize": 14,
    "axes.labelsize": 13,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
    "legend.fontsize": 12,
}
plt.rcParams.update(STYLE)

# ── naming maps ──────────────────────────────────────────────────────────
EXTRACTOR_FULL = {
    "efficientnetb1_finetuned": "EfficientNetB1 FT",
    "resnet50_finetuned": "ResNet50 FT",
    "mobilenetv2_finetuned": "MobileNetV2 FT",
    "efficientnetb1": "EfficientNetB1 PT",
    "resnet50": "ResNet50 PT",
    "mobilenetv2": "MobileNetV2 PT",
    "colorhistogram": "ColorHist HSV",
    "colorhistogramhs": "ColorHist HS",
    "hog": "HOG",
    "gabor": "Gabor",
}

EXTRACTOR_CATEGORY = {
    "efficientnetb1_finetuned": "Finetuned",
    "resnet50_finetuned": "Finetuned",
    "mobilenetv2_finetuned": "Finetuned",
    "efficientnetb1": "Pretrained",
    "resnet50": "Pretrained",
    "mobilenetv2": "Pretrained",
    "colorhistogram": "Traditional",
    "colorhistogramhs": "Traditional",
    "hog": "Traditional",
    "gabor": "Traditional",
}

AGG_FULL = {
    "freq_strength": "Freq×Strength",
    "weighted": "Weighted",
    "uni": "Uniform",
    "relative": "Relative",
    "per_species_avg": "Per-Species Avg",
    "max_score": "Max Score",
    "perquery_avg": "Per-Query Avg",
    "perquery_norm_avg": "Per-Query Norm Avg",
}

ENV_FULL = {
    "E1": "Same Medium (E1)",
    "E2": "All Media (E2)",
    "E3_CREA": "CREA (E3)",
    "E3_CYA": "CYA (E3)",
    "E3_CYA30": "CYA30 (E3)",
    "E3_CYAS": "CYAS (E3)",
    "E3_DG18": "DG18 (E3)",
    "E3_MEA": "MEA (E3)",
    "E3_OA": "OA (E3)",
    "E3_YES": "YES (E3)",
    "E4_CREA": "All-Except CREA (E4)",
    "E4_CYA": "All-Except CYA (E4)",
    "E4_CYA30": "All-Except CYA30 (E4)",
    "E4_CYAS": "All-Except CYAS (E4)",
    "E4_DG18": "All-Except DG18 (E4)",
    "E4_MEA": "All-Except MEA (E4)",
    "E4_OA": "All-Except OA (E4)",
    "E4_YES": "All-Except YES (E4)",
}

FT_COLOR = "#1f77b4"
PT_COLOR = "#ff7f0e"
TR_COLOR = "#2ca02c"
YOLO_COLOR = "#2ecc71"
KMEANS_COLOR = "#3498db"


# ═══════════════════════════════════════════════════════════════════════════
# Data collection
# ═══════════════════════════════════════════════════════════════════════════

def parse_folder_name(name: str) -> Optional[Dict]:
    """Parse '{extractor}_{k}_{agg}_{env}_{seg}' folder name."""
    m = re.match(
        r"^(.+?)_(\d+)_(freq_strength|weighted|uni|relative|per_species_avg|"
        r"max_score|perquery_avg|perquery_norm_avg)_"
        r"(E\d(?:_\w+)?)_(yolo|kmeans)$", name
    )
    if not m:
        return None
    return {
        "extractor": m.group(1),
        "k": int(m.group(2)),
        "agg": m.group(3),
        "env": m.group(4),
        "seg": m.group(5),
    }


def collect_all_results() -> pd.DataFrame:
    """Scan all results/retrieval_*/ for evaluation_results.json."""
    rows = []
    for rd in sorted(RESULTS_DIR.iterdir()):
        if not rd.is_dir() or not rd.name.startswith("retrieval_"):
            continue
        for sub in rd.iterdir():
            if not sub.is_dir():
                continue
            jf = sub / "evaluation_results.json"
            if not jf.exists():
                continue
            parsed = parse_folder_name(sub.name)
            if not parsed:
                continue
            data = json.loads(jf.read_text())
            rows.append({
                **parsed,
                "accuracy": data["overall_accuracy"],
                "correct": data.get("correct_predictions", 0),
                "total": data.get("total_strains", 0),
                "source_dir": str(sub),
            })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["extractor_full"] = df["extractor"].map(EXTRACTOR_FULL).fillna(df["extractor"])
        df["agg_full"] = df["agg"].map(AGG_FULL).fillna(df["agg"])
        df["env_full"] = df["env"].map(ENV_FULL).fillna(df["env"])
        df["category"] = df["extractor"].map(EXTRACTOR_CATEGORY).fillna("Unknown")
        df["label"] = df.apply(
            lambda r: f"{r['extractor_full']} | {r['env']} | {r['agg_full']}", axis=1
        )
    return df


def run_missing_evaluations(df: pd.DataFrame) -> None:
    """Run targeted missing configs for kmeans collection and needed K values."""
    print("\nChecking for missing evaluation configs...")

    # What we need for yolo (qdrant-research) collection:
    # - K values: 3, 5, 7, 11 (we already have K=11)
    # - extractors: all 10, envs: E1, E2, E3_CREA, aggs: freq_strength
    # - plus full agg sweep for top extractors at key K values

    # For kmeans collection:
    # - extractors: colorhistogram, efficientnetb1_finetuned
    # - envs: E1, E3_CREA
    # - aggs: freq_strength
    # - K: 5

    needed_yolo = _build_needed_configs("yolo", df)
    needed_kmeans = _build_needed_configs("kmeans", df)

    total_needed = needed_yolo + needed_kmeans
    print(f"  Need {len(needed_yolo)} yolo configs, {len(needed_kmeans)} kmeans configs")

    if not total_needed:
        print("  All needed evaluations already exist.")
        return

    # Run in parallel
    from src.experiments.retrieval.run import run_comprehensive_report

    # Group by collection and K to call run_comprehensive_report efficiently
    by_collection_k: Dict[Tuple[str, int], Dict[str, List[str]]] = {}
    for cfg in total_needed:
        key = (cfg["collection"], cfg["k"])
        if key not in by_collection_k:
            by_collection_k[key] = {"extractors": set(), "envs": set(), "aggs": set()}
        by_collection_k[key]["extractors"].add(cfg["extractor"])
        by_collection_k[key]["envs"].add(cfg["env"])
        by_collection_k[key]["aggs"].add(cfg["agg"])

    print(f"  Running {len(by_collection_k)} evaluation batches...")
    for (coll, k_val), configs in sorted(by_collection_k.items()):
        extractors = sorted(configs["extractors"])
        envs = sorted(configs["envs"])
        aggs = sorted(configs["aggs"])
        coll_name = "qdrant-research" if coll == "yolo" else "kmeans_features"
        output_root = RESULTS_DIR / f"retrieval_report_charts_{coll}_k{k_val}"

        print(f"  Collection={coll_name} K={k_val}")
        print(f"    Extractors: {extractors}")
        print(f"    Envs: {envs}")
        print(f"    Aggs: {aggs}")
        try:
            run_comprehensive_report(
                identifier=f"report_charts_{coll}_k{k_val}",
                extractors=extractors,
                env_strategies=envs,
                agg_strategies=aggs,
                k=k_val,
                max_visualizations=10,
                visualize_correct=True,
                visualize_incorrect=True,
                collection_name=coll_name,
                output_root=output_root,
            )
        except Exception as e:
            print(f"    ERROR: {e}")

    print("  Done running missing evaluations.")


def _build_needed_configs(seg_type: str, existing_df: pd.DataFrame) -> List[Dict]:
    """Build list of needed config dicts for a segmentation type."""
    existing = existing_df[existing_df["seg"] == seg_type] if not existing_df.empty else pd.DataFrame()

    # Core extractors for coverage
    extractors = [
        "efficientnetb1_finetuned", "resnet50_finetuned", "mobilenetv2_finetuned",
        "efficientnetb1", "resnet50", "mobilenetv2",
        "colorhistogram", "colorhistogramhs", "hog", "gabor",
    ]

    # For kmeans, only need specific configs for comparison
    if seg_type == "kmeans":
        extractors = ["colorhistogram", "efficientnetb1_finetuned"]
        envs = ["E1", "E3_CREA"]
        aggs = ["freq_strength"]
        k_values = [5]
    else:
        # For yolo, need coverage for heatmaps + top-15
        envs = ["E1", "E2", "E3_CREA", "E3_MEA", "E3_YES", "E3_DG18"]
        aggs = ["freq_strength", "weighted", "relative", "uni", "per_species_avg",
                "max_score", "perquery_avg", "perquery_norm_avg"]
        k_values = [3, 5, 7]

    coll_name = "qdrant-research" if seg_type == "yolo" else "kmeans_features"

    needed = []
    for ext in extractors:
        for env in envs:
            for agg in aggs:
                for k in k_values:
                    if not existing.empty:
                        match = existing[
                            (existing["extractor"] == ext) &
                            (existing["env"] == env) &
                            (existing["agg"] == agg) &
                            (existing["k"] == k)
                        ]
                        if not match.empty:
                            continue
                    needed.append({
                        "extractor": ext,
                        "env": env,
                        "agg": agg,
                        "k": k,
                        "collection": seg_type,
                        "coll_name": coll_name,
                    })
    return needed


# ═══════════════════════════════════════════════════════════════════════════
# Chart 1: Top-15 bar chart
# ═══════════════════════════════════════════════════════════════════════════

def chart_top15_accuracy(df: pd.DataFrame):
    """Top-15 accuracy bar chart — freq_strength + E1 only, isolating extractor differences."""
    if df.empty:
        print("  No data for top-15 chart")
        return

    # Fix: freq_strength + E1 only — shows feature extractor differences in isolation
    filtered = df[(df["seg"] == "yolo") & (df["agg"] == "freq_strength") & (df["env"] == "E1")]
    if filtered.empty:
        filtered = df[df["seg"] == "yolo"]
    if filtered.empty:
        filtered = df

    yolo_df = filtered

    top = yolo_df.nlargest(15, "accuracy").copy()
    top["short_label"] = top.apply(
        lambda r: f"{r['extractor_full']}\nK={int(r['k'])}", axis=1
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    colors = [FT_COLOR if ft == "Finetuned" else PT_COLOR if ft == "Pretrained" else TR_COLOR
              for ft in top["category"]]
    bars = ax.bar(range(len(top)), top["accuracy"] * 100, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top["short_label"], fontsize=5, rotation=30, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Top 15 Retrieval Configurations — YOLO Segments (qdrant-research)")
    ax.set_ylim(0, max(top["accuracy"]) * 115)

    for bar, acc in zip(bars, top["accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{acc*100:.1f}%", ha="center", va="bottom", fontsize=6, fontweight="bold")

    ax.legend(handles=[
        plt.matplotlib.patches.Patch(facecolor=FT_COLOR, label="Fine-tuned DL"),
        plt.matplotlib.patches.Patch(facecolor=PT_COLOR, label="Pretrained DL"),
        plt.matplotlib.patches.Patch(facecolor=TR_COLOR, label="Traditional"),
    ], loc="lower right", fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save("retrieval_top15_accuracy.png", fig)

    # Save CSV table
    table = top[["extractor_full", "env", "agg_full", "k", "accuracy"]].copy()
    table["accuracy_pct"] = (table["accuracy"] * 100).round(1)
    table = table.rename(columns={"extractor_full": "Extractor", "env": "Media Strategy",
                                   "agg_full": "Aggregation", "k": "K"})
    table = table[["Extractor", "Media Strategy", "Aggregation", "K", "accuracy_pct"]]
    table.to_csv(LATEX_FIGURES / "10_tables" / "table_top15_accuracy.csv", index=False)
    table.to_csv(REPORT_FIGURES / "10_tables" / "table_top15_accuracy.csv", index=False)
    print(f"  saved retrieval_top15_accuracy.png + table")


# ═══════════════════════════════════════════════════════════════════════════
# Chart 2: KMeans vs YOLO comparison
# ═══════════════════════════════════════════════════════════════════════════

def chart_seg_comparison(df: pd.DataFrame):
    """KMeans vs YOLO bar chart for specific configs."""
    if df.empty:
        print("  No data for seg comparison")
        return

    # Target configs: colorhistogram E1 K=5 freq_strength,
    #                effb1_finetuned E1 K=5 freq_strength,
    #                effb1_finetuned E3_CREA K=5 freq_strength
    target_configs = [
        ("colorhistogram", "E1", "freq_strength", 5),
        ("efficientnetb1_finetuned", "E1", "freq_strength", 5),
        ("efficientnetb1_finetuned", "E3_CREA", "freq_strength", 5),
    ]

    entries = []
    for ext, env, agg, k in target_configs:
        for seg in ["yolo", "kmeans"]:
            match = df[(df["extractor"] == ext) & (df["env"] == env) &
                       (df["agg"] == agg) & (df["k"] == k) & (df["seg"] == seg)]
            if not match.empty:
                row = match.iloc[0]
                entries.append({
                    "label": f"{EXTRACTOR_FULL.get(ext, ext)}\n{ENV_FULL.get(env, env)}",
                    "seg": seg,
                    "accuracy": row["accuracy"],
                })

    if not entries:
        print("  No seg comparison data found")
        return

    cf = pd.DataFrame(entries)
    unique_labels = cf["label"].unique()

    fig, ax = plt.subplots(figsize=(10, 6))
    x_pos = np.arange(len(unique_labels))
    w = 0.35

    for i, seg in enumerate(["yolo", "kmeans"]):
        seg_data = cf[cf["seg"] == seg]
        values = []
        for lbl in unique_labels:
            match = seg_data[seg_data["label"] == lbl]
            values.append(match["accuracy"].values[0] * 100 if not match.empty else 0)
        offset = (i - 0.5) * w
        color = YOLO_COLOR if seg == "yolo" else KMEANS_COLOR
        label = "YOLO Segments" if seg == "yolo" else "K-Means Segments"
        bars = ax.bar(x_pos + offset, values, w, label=label, color=color, edgecolor="white")
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                        f"{val:.1f}%", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xticks(x_pos)
    ax.set_xticklabels(unique_labels, fontsize=7)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("YOLO vs K-Means Segmentation — Retrieval Accuracy (K=5, freq_strength)")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    _save("retrieval_yolo_vs_kmeans.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# Chart 3: Heatmaps + stats table
# ═══════════════════════════════════════════════════════════════════════════

def chart_hyperparam_heatmaps(df: pd.DataFrame):
    """Chapter 2 retrieval comparison charts for media, K, and aggregation."""
    if df.empty:
        print("  No data for heatmaps")
        return

    yolo_df = df[df["seg"] == "yolo"]

    # Best extractors: top 3 fine-tuned
    ft_extractors = ["efficientnetb1_finetuned", "resnet50_finetuned", "mobilenetv2_finetuned"]
    best_df = yolo_df[yolo_df["extractor"].isin(ft_extractors)]

    if best_df.empty:
        print("  No best extractor data for heatmaps")
        return

    # Figure 2.23: best result within each media strategy for EfficientNetB1 FT + YOLO
    media_df = yolo_df[
        (yolo_df["extractor"] == "efficientnetb1_finetuned")
        & (yolo_df["seg"] == "yolo")
    ]
    _media_strategy_bar(media_df)

    # ── K × Agg heatmap (mean across best extractors, all envs) ──
    _heatmap(
        best_df, index_col="k", columns_col="agg",
        index_label="K", columns_label="Aggregation Strategy",
        title="K × Aggregation Strategy (mean across best FT extractors, all envs)",
        filename="retrieval_heatmap_k_vs_agg.png",
    )

    # ── Agg × Media heatmap (mean across best extractors, all K) ──
    _heatmap(
        best_df, index_col="agg", columns_col="env",
        index_label="Aggregation Strategy", columns_label="Media Strategy",
        title="Aggregation Strategy × Media (mean across best FT extractors, all K)",
        filename="retrieval_heatmap_agg_vs_media.png",
    )

    # ── Hyperparameter stats table ──
    _hyperparam_stats_table(yolo_df)


def _media_strategy_bar(df: pd.DataFrame):
    """Best result by media strategy for EfficientNetB1 fine-tuned YOLO retrieval."""
    if df.empty:
        print("  No data for media strategy bar chart")
        return

    ranked = (
        df.sort_values(["accuracy", "k"], ascending=[False, True])
        .groupby("env", as_index=False)
        .first()
    )

    media_order = ["E1", "E2", "E3_CREA", "E3_DG18", "E3_MEA", "E3_YES", "E3_CYA", "E3_CYA30", "E3_CYAS", "E3_OA"]
    ranked["env"] = pd.Categorical(ranked["env"], categories=media_order, ordered=True)
    ranked = ranked.sort_values(["env", "accuracy"], ascending=[True, False]).dropna(subset=["env"])
    if ranked.empty:
        print("  No ranked media strategy data")
        return

    labels = [ENV_FULL.get(env, env) for env in ranked["env"]]
    values = ranked["accuracy"] * 100
    colors = [YOLO_COLOR if env in {"E1", "E2"} else KMEANS_COLOR for env in ranked["env"]]

    fig, ax = plt.subplots(figsize=(13.5, 7.2))
    y = np.arange(len(ranked))
    bars = ax.barh(y, values, color=colors, edgecolor="white", linewidth=0.8, height=0.45)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=13)
    ax.invert_yaxis()
    ax.set_xlabel("Best Accuracy (%)", fontsize=13)
    ax.set_title("Best Retrieval Result by Media Strategy — EfficientNetB1 FT + YOLO", fontsize=15)
    ax.set_xlim(0, max(100, values.max() * 1.22))

    for bar, row in zip(bars, ranked.itertuples(index=False)):
        ax.text(
            bar.get_width() + 0.8,
            bar.get_y() + bar.get_height() / 2,
            f"{row.accuracy*100:.1f}% | {AGG_FULL.get(row.agg, row.agg)} | K={int(row.k)}",
            va="center",
            fontsize=12,
        )

    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save("retrieval_heatmap_k_vs_media.png", fig)



def _heatmap(df, index_col, columns_col, index_label, columns_label, title, filename):
    pivot = df.pivot_table(index=index_col, columns=columns_col,
                           values="accuracy", aggfunc="mean")

    index_vals = sorted(df[index_col].unique())
    col_vals = sorted(df[columns_col].unique())

    mat = np.zeros((len(index_vals), len(col_vals)))
    for i, iv in enumerate(index_vals):
        for j, cv in enumerate(col_vals):
            if iv in pivot.index and cv in pivot.columns:
                mat[i, j] = pivot.loc[iv, cv] if not pd.isna(pivot.loc[iv, cv]) else 0

    if index_col == "k":
        index_labels = [f"K={k}" for k in index_vals]
    else:
        index_labels = [AGG_FULL.get(v, v)[:18] for v in index_vals]

    if columns_col == "env":
        col_labels = [ENV_FULL.get(v, v)[:20] for v in col_vals]
    elif columns_col == "agg":
        col_labels = [AGG_FULL.get(v, v)[:18] for v in col_vals]
    else:
        col_labels = col_vals

    h, w = len(index_vals) * 0.6 + 1, len(col_vals) * 0.8 + 1
    fig, ax = plt.subplots(figsize=(max(w, 9), max(h, 5)))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(col_vals)))
    ax.set_xticklabels(col_labels, fontsize=10, rotation=30, ha="right")
    ax.set_yticks(range(len(index_vals)))
    ax.set_yticklabels(index_labels, fontsize=10)
    ax.set_title(title, fontsize=12)
    ax.set_xlabel(columns_label, fontsize=11)
    ax.set_ylabel(index_label, fontsize=11)

    for i in range(len(index_vals)):
        for j in range(len(col_vals)):
            v = mat[i, j]
            if v > 0:
                fc = "white" if v > 0.65 else "black"
                ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=7, color=fc, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Mean Accuracy")
    fig.tight_layout()
    _save(filename, fig)


def _hyperparam_stats_table(df: pd.DataFrame):
    """Generate min/mean/max accuracy table per hyperparameter value."""
    rows = []

    # By extractor (best ones only: FT extractors)
    ft_extractors = ["efficientnetb1_finetuned", "resnet50_finetuned", "mobilenetv2_finetuned"]
    for ext in sorted(df["extractor"].unique()):
        sub = df[df["extractor"] == ext]
        if sub.empty:
            continue
        rows.append({
            "Parameter": "Extractor",
            "Value": EXTRACTOR_FULL.get(ext, ext),
            "Min": sub["accuracy"].min(),
            "Mean": sub["accuracy"].mean(),
            "Max": sub["accuracy"].max(),
            "Count": len(sub),
            "Is_Best": ext in ft_extractors,
        })

    # By K
    for k in sorted(df["k"].unique()):
        sub = df[df["k"] == k]
        if sub.empty:
            continue
        rows.append({
            "Parameter": "K",
            "Value": f"K={k}",
            "Min": sub["accuracy"].min(),
            "Mean": sub["accuracy"].mean(),
            "Max": sub["accuracy"].max(),
            "Count": len(sub),
            "Is_Best": k <= 7,
        })

    # By media
    for env in sorted(df["env"].unique()):
        sub = df[df["env"] == env]
        if sub.empty:
            continue
        rows.append({
            "Parameter": "Media",
            "Value": ENV_FULL.get(env, env),
            "Min": sub["accuracy"].min(),
            "Mean": sub["accuracy"].mean(),
            "Max": sub["accuracy"].max(),
            "Count": len(sub),
            "Is_Best": env in {"E1", "E2"},
        })

    # By aggregation
    for agg in sorted(df["agg"].unique()):
        sub = df[df["agg"] == agg]
        if sub.empty:
            continue
        rows.append({
            "Parameter": "Aggregation",
            "Value": AGG_FULL.get(agg, agg),
            "Min": sub["accuracy"].min(),
            "Mean": sub["accuracy"].mean(),
            "Max": sub["accuracy"].max(),
            "Count": len(sub),
            "Is_Best": agg == "freq_strength",
        })

    table = pd.DataFrame(rows)
    for col in ["Min", "Mean", "Max"]:
        table[f"{col}_pct"] = (table[col] * 100).round(1)
    table = table.sort_values("Mean", ascending=False)
    table = table[["Parameter", "Value", "Min_pct", "Mean_pct", "Max_pct", "Count"]]
    table.columns = ["Parameter", "Value", "Min (%)", "Mean (%)", "Max (%)", "Samples"]

    table_path = LATEX_FIGURES / "10_tables" / "table_hyperparam_stats.csv"
    table.to_csv(table_path, index=False)
    table.to_csv(REPORT_FIGURES / "10_tables" / "table_hyperparam_stats.csv", index=False)

    latex_path = LATEX_FIGURES / "10_tables" / "table_hyperparam_stats.tex"
    _write_latex_table(table, latex_path, "Hyperparameter Statistics: Min/Mean/Max Accuracy")
    print(f"  saved hyperparam stats table + LaTeX")


def _write_latex_table(df, path, caption):
    """Write pandas DataFrame as a LaTeX table."""
    lines = [
        "\\begin{table}[ht]",
        "\\centering",
        f"\\caption{{{caption}}}",
        "\\begin{tabularx}{\\textwidth}{@{}l X r r r r@{}}",
        "\\toprule",
    ]
    # Header
    cols = list(df.columns)
    lines.append(" & ".join(f"\\textbf{{{c}}}" for c in cols) + " \\\\")
    lines.append("\\midrule")

    for _, row in df.iterrows():
        vals = []
        for i, c in enumerate(cols):
            v = row[c]
            if isinstance(v, float):
                vals.append(f"{v:.1f}")
            elif isinstance(v, int):
                vals.append(str(v))
            else:
                vals.append(str(v).replace("_", "\\_").replace("%", "\\%"))
        lines.append(" & ".join(vals) + " \\\\")
    lines.extend([
        "\\bottomrule",
        "\\end{tabularx}",
        "\\end{table}",
    ])

    path.write_text("\n".join(lines))


# ═══════════════════════════════════════════════════════════════════════════
# Chart: Extractor category comparison (additional)
# ═══════════════════════════════════════════════════════════════════════════

def chart_extractor_family(df: pd.DataFrame):
    """Grouped extractor summary with mean/min/max markers."""
    if df.empty:
        return

    yolo_df = df[df["seg"] == "yolo"]
    if yolo_df.empty:
        yolo_df = df

    ext_stats = yolo_df.groupby("extractor").agg(
        mean=("accuracy", "mean"),
        min=("accuracy", "min"),
        max=("accuracy", "max"),
    ).reset_index()
    ext_stats["extractor_full"] = ext_stats["extractor"].map(EXTRACTOR_FULL).fillna(ext_stats["extractor"])
    ext_stats = ext_stats.sort_values("mean", ascending=True)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = [FT_COLOR if "finetuned" in e else PT_COLOR if e in {"resnet50", "efficientnetb1", "mobilenetv2"}
              else TR_COLOR for e in ext_stats["extractor"]]
    y = np.arange(len(ext_stats))
    bars = ax.barh(y, ext_stats["mean"] * 100, color=colors, edgecolor="white", linewidth=0.5, height=0.6)
    ax.scatter(ext_stats["max"] * 100, y, color="black", s=22, zorder=3)
    for yi, min_v, max_v in zip(y, ext_stats["min"] * 100, ext_stats["max"] * 100):
        ax.hlines(yi, min_v, max_v, colors="black", linewidth=1.2, zorder=2)
        ax.vlines(min_v, yi - 0.12, yi + 0.12, colors="black", linewidth=1.0, zorder=2)
    ax.set_yticks(y)
    ax.set_yticklabels(ext_stats["extractor_full"], fontsize=7)
    ax.set_xlabel("Accuracy (%)")
    ax.set_title("Feature Extractor Summary Across Retrieval Settings")
    ax.set_xlim(0, 100)

    for bar, mean_v, min_v, max_v in zip(bars, ext_stats["mean"], ext_stats["min"], ext_stats["max"]):
        ax.text(max_v * 100 + 0.6, bar.get_y() + bar.get_height() / 2,
                f"mean {mean_v*100:.1f}% | min {min_v*100:.1f}% | max {max_v*100:.1f}%",
                va="center", fontsize=6)

    legend_handles = [
        plt.matplotlib.patches.Patch(facecolor=FT_COLOR, label="Fine-tuned"),
        plt.matplotlib.patches.Patch(facecolor=PT_COLOR, label="Pretrained"),
        plt.matplotlib.patches.Patch(facecolor=TR_COLOR, label="Traditional"),
        plt.matplotlib.lines.Line2D([0], [0], color="black", linewidth=1.2, label="Min–Max"),
        plt.matplotlib.lines.Line2D([0], [0], color="black", marker="o", linestyle="None", markersize=4, label="Max"),
        plt.matplotlib.patches.Patch(facecolor="#777777", label="Mean"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=7)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    _save("retrieval_extractor_family.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _save(name: str, fig=None, subfolder: str = "06_retrieval"):
    if fig is None:
        return
    for outdir in (LATEX_FIGURES, REPORT_FIGURES):
        out = outdir / subfolder / name
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {subfolder}/{name}")


def _collect_prediction_samples(df: pd.DataFrame):
    """Find and copy some sample prediction visualizations."""
    # Find directories with visualization subfolders
    viz_dirs = []
    for rd in sorted(RESULTS_DIR.iterdir()):
        if not rd.is_dir() or not rd.name.startswith("retrieval_"):
            continue
        for sub in rd.iterdir():
            if not sub.is_dir():
                continue
            correct_dir = sub / "visualizations" / "correct"
            incorrect_dir = sub / "visualizations" / "incorrect"
            if correct_dir.exists():
                # Pick first 2 images
                imgs = sorted(correct_dir.glob("*.png"))[:2]
                viz_dirs.append(("correct", correct_dir, imgs))
            if incorrect_dir.exists():
                imgs = sorted(incorrect_dir.glob("*.png"))[:2]
                viz_dirs.append(("incorrect", incorrect_dir, imgs))

    if not viz_dirs:
        return

    # Copy one correct and one incorrect sample to figures
    import shutil
    for vtype, vdir, imgs in viz_dirs[:4]:
        for img in imgs:
            dest = LATEX_FIGURES / f"pred_{vtype}_{img.name}"
            shutil.copy2(img, dest)
    print(f"  copied prediction visualization samples")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("MycoAI Retrieval Report: Chart Generation")
    print("=" * 60)

    # 1. Collect existing results
    print("\n[1/5] Collecting existing evaluation results...")
    sys.path.insert(0, str(PROJECT / "research"))
    df = collect_all_results()
    print(f"  Found {len(df)} evaluation results")

    if not df.empty:
        print(f"  Seg types: {df['seg'].unique().tolist()}")
        print(f"  K values: {sorted(df['k'].unique())}")
        print(f"  Extractors: {sorted(df['extractor'].unique())}")

    # 2. Run missing evaluations
    print("\n[2/5] Running missing evaluations...")
    try:
        run_missing_evaluations(df)
    except Exception as e:
        print(f"  WARNING: Evaluation run failed: {e}")
        print("  Continuing with existing data only...")

    # Re-collect after running evaluations
    df = collect_all_results()
    print(f"  Total results after evaluation: {len(df)}")

    # 3. Generate charts
    print("\n[3/5] Generating charts...")
    chart_top15_accuracy(df)
    chart_seg_comparison(df)
    chart_hyperparam_heatmaps(df)
    chart_extractor_family(df)

    # 4. Collect prediction visualizations
    print("\n[4/5] Collecting prediction visualization samples...")
    _collect_prediction_samples(df)

    # 5. Summary
    print("\n[5/5] Summary:")
    if not df.empty:
        yolo_df = df[df["seg"] == "yolo"]
        best = df.nlargest(1, "accuracy").iloc[0]
        print(f"  Best accuracy: {best['accuracy']:.4f} ({best['extractor_full']} | "
              f"{best['env']} | {best['agg_full']} | K={best['k']} | {best['seg']})")

        if not yolo_df.empty:
            print(f"  YOLO configs: {len(yolo_df)}")
            for ext in sorted(yolo_df["extractor"].unique()):
                sub = yolo_df[yolo_df["extractor"] == ext]
                print(f"    {EXTRACTOR_FULL.get(ext, ext):25s}  mean={sub['accuracy'].mean():.4f}  "
                      f"max={sub['accuracy'].max():.4f}  n={len(sub)}")

    print(f"\n  Charts saved to: {LATEX_FIGURES}")
    print("Done.")


if __name__ == "__main__":
    main()
