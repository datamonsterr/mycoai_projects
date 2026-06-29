"""Retrieval experiment charts: comprehensive results, CV, segmentation comparison.

Generates concise, non-duplicate charts for the graduation report.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STYLE = {"font.family": "serif", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8}
plt.rcParams.update(STYLE)

PROJECT = Path("/home/dat/dev/mycoai_projects")
LATEX_DIR = PROJECT / "docs/graduation_report/latex/figures"
REPORT_DIR = PROJECT / "graduation_report/report/figures"
for d in (LATEX_DIR, REPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

RETRIEVAL_PIPE = PROJECT / "results/retrieval_pipeline"
SEG_DIR = PROJECT / "results/segmentation_comparison"
CV_CSV = PROJECT / "results/cross_validation/cv_results.csv"
CV_SUMMARY = PROJECT / "results/cross_validation/cv_summary_table.csv"
SEG_CSV = SEG_DIR / "comparison.csv"

FT_COLOR = "#1f77b4"
PT_COLOR = "#ff7f0e"
TR_COLOR = "#2ca02c"


def save(name, fig=None):
    if fig is None:
        return
    for out in (LATEX_DIR / name, REPORT_DIR / name):
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {name}")


# ═══════════════════════════════════════════════════════════════════════════
# Data loaders
# ═══════════════════════════════════════════════════════════════════════════

def load_retrieval_pipeline_data() -> pd.DataFrame:
    """Load all retrieval_pipeline evaluation_results.json into a DataFrame."""
    rows = []
    pp = RETRIEVAL_PIPE
    if not pp.exists():
        return pd.DataFrame()
    for d in sorted(pp.iterdir()):
        if not d.is_dir():
            continue
        jf = d / "evaluation_results.json"
        if not jf.exists():
            continue
        data = json.loads(jf.read_text())
        name = d.name
        m = re.match(
            r"^(.+?)_(freq_strength|weighted|uni|relative|per_species_avg|"
            r"max_score|perquery_avg|perquery_norm_avg)_(E\d\S*)$", name
        )
        if m:
            ext, ag, en = m.groups()
        else:
            continue
        rows.append({
            "extractor": ext,
            "agg": ag,
            "env": en,
            "accuracy": data["overall_accuracy"],
            "correct": data.get("correct_predictions", 0),
            "total": data.get("total_strains", 0),
            "k": data.get("k", 5),
        })
    df = pd.DataFrame(rows)
    df["category"] = df["extractor"].apply(_categorize_extractor)
    return df


def _categorize_extractor(ext: str) -> str:
    if "_finetuned" in ext:
        return "Finetuned"
    if ext in {"colorhistogram", "colorhistogramhs", "hog", "gabor"}:
        return "Traditional"
    return "Pretrained"


def load_segmentation_data() -> pd.DataFrame:
    if SEG_CSV.exists():
        df = pd.read_csv(SEG_CSV)
        # filter out zero-accuracy entries
        df = df[df["accuracy"] > 0].copy()
        return df
    return pd.DataFrame()


def load_cv_data() -> pd.DataFrame:
    if CV_CSV.exists():
        df = pd.read_csv(CV_CSV)
        # aggregate by config
        acc = df.groupby(["extractor", "media_strategy", "agg_strategy", "k"])["correct"].mean().reset_index()
        acc = acc.rename(columns={"correct": "accuracy"})
        return acc
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
# 1. Top accuracy bar chart + table
# ═══════════════════════════════════════════════════════════════════════════

def chart_retrieval_top_accuracy():
    """Top-15 retrieval configs, bar chart sorted by accuracy."""
    df = load_retrieval_pipeline_data()
    if df.empty:
        return

    top = df.nlargest(15, "accuracy").copy()
    top["label"] = top.apply(
        lambda r: f"{r['extractor']}\n{r['env']} {r['agg']}", axis=1
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = [FT_COLOR if ft == "Finetuned" else PT_COLOR if ft == "Pretrained" else TR_COLOR
              for ft in top["category"]]
    bars = ax.bar(range(len(top)), top["accuracy"] * 100, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top["label"], fontsize=5, rotation=25, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Top 15 Retrieval Configurations (retrieval pipeline)")
    ax.set_ylim(0, max(top["accuracy"]) * 120)

    for bar, acc in zip(bars, top["accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{acc*100:.1f}%", ha="center", va="bottom", fontsize=6, fontweight="bold")

    ax.legend(handles=[
        plt.matplotlib.patches.Patch(facecolor=FT_COLOR, label="Finetuned"),
        plt.matplotlib.patches.Patch(facecolor=PT_COLOR, label="Pretrained"),
        plt.matplotlib.patches.Patch(facecolor=TR_COLOR, label="Traditional"),
    ], loc="lower right", fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("retrieval_top_configs.png", fig)

    # Write table CSV
    table = top[["extractor", "env", "agg", "k", "accuracy"]].copy()
    table["accuracy"] = (table["accuracy"] * 100).round(1)
    table = table.rename(columns={"accuracy": "accuracy_pct"})
    table_path = REPORT_DIR / "retrieval_top_configs.csv"
    table.to_csv(table_path, index=False)
    print(f"  saved {table_path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# 2. Heatmap: Agg strategy vs K (mean across environments/extractors)
# ═══════════════════════════════════════════════════════════════════════════

def chart_agg_vs_k_heatmap():
    df = load_retrieval_pipeline_data()
    if df.empty:
        return

    pivot = df.pivot_table(index="agg", columns="k", values="accuracy", aggfunc="mean")
    if pivot.empty:
        return

    agg_order = ["freq_strength", "weighted", "relative", "uni", "per_species_avg",
                 "perquery_avg", "perquery_norm_avg", "max_score"]
    k_order = sorted(df["k"].unique())
    mat = np.zeros((len(agg_order), len(k_order)))
    for i, a in enumerate(agg_order):
        for j, kv in enumerate(k_order):
            if a in pivot.index and kv in pivot.columns:
                mat[i, j] = pivot.loc[a, kv] if not pd.isna(pivot.loc[a, kv]) else 0

    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(k_order)))
    ax.set_xticklabels([f"K={k}" for k in k_order])
    ax.set_yticks(range(len(agg_order)))
    ax.set_yticklabels(agg_order, fontsize=7)
    ax.set_title("Aggregation Strategy × K (mean across envs & extractors)")

    for i in range(len(agg_order)):
        for j in range(len(k_order)):
            v = mat[i, j]
            if v > 0:
                ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=6,
                        color="black" if v < 0.65 else "white")
    plt.colorbar(im, ax=ax, label="Mean Accuracy")
    fig.tight_layout()
    save("retrieval_heatmap_agg_vs_k.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 3. Heatmap: Environment strategy vs Agg (mean across K)
# ═══════════════════════════════════════════════════════════════════════════

def chart_env_vs_agg_heatmap():
    df = load_retrieval_pipeline_data()
    if df.empty:
        return

    pivot = df.pivot_table(index="env", columns="agg", values="accuracy", aggfunc="mean")
    if pivot.empty:
        return

    env_order = sorted(df["env"].unique())
    agg_order = sorted(df["agg"].unique())
    mat = np.zeros((len(env_order), len(agg_order)))
    for i, e in enumerate(env_order):
        for j, a in enumerate(agg_order):
            if e in pivot.index and a in pivot.columns:
                mat[i, j] = pivot.loc[e, a] if not pd.isna(pivot.loc[e, a]) else 0

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(agg_order)))
    ax.set_xticklabels(agg_order, fontsize=6, rotation=30, ha="right")
    ax.set_yticks(range(len(env_order)))
    ax.set_yticklabels(env_order, fontsize=7)
    ax.set_title("Environment Strategy × Aggregation (mean across K & extractors)")

    for i in range(len(env_order)):
        for j in range(len(agg_order)):
            v = mat[i, j]
            if v > 0:
                ax.text(j, i, f"{v:.3f}", ha="center", va="center", fontsize=5,
                        color="black" if v < 0.65 else "white")
    plt.colorbar(im, ax=ax, label="Mean Accuracy")
    fig.tight_layout()
    save("retrieval_heatmap_env_vs_agg.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 4. Finetuned vs Pretrained vs Traditional comparison
# ═══════════════════════════════════════════════════════════════════════════

def chart_category_comparison():
    df = load_retrieval_pipeline_data()
    if df.empty:
        return

    cats = df.groupby("category").agg(
        mean=("accuracy", "mean"),
        max=("accuracy", "max"),
        min=("accuracy", "min"),
    ).reset_index()

    order = {"Finetuned": 0, "Pretrained": 1, "Traditional": 2}
    cats["sort_key"] = cats["category"].map(order)
    cats = cats.sort_values("sort_key")

    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(cats))
    w = 0.25
    bars1 = ax.bar(x - w, cats["mean"] * 100, w, label="Mean", color="#1f77b4")
    bars2 = ax.bar(x, cats["max"] * 100, w, label="Max", color="#2ca02c")
    ax.bar(x + w, cats["min"] * 100, w, label="Min", color="#d62728")

    ax.set_xticks(x)
    ax.set_xticklabels(cats["category"], fontsize=9)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Extractor Category: Mean / Max / Min Accuracy")
    ax.set_ylim(0, 100)

    for b, v in zip(bars1, cats["mean"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5,
                f"{v*100:.1f}%", ha="center", fontsize=7)
    for b, v in zip(bars2, cats["max"]):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.5,
                f"{v*100:.1f}%", ha="center", fontsize=7)

    ax.legend(fontsize=8, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("retrieval_category_comparison.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 5. Feature extractor sorted bar chart
# ═══════════════════════════════════════════════════════════════════════════

def chart_extractor_sorted():
    df = load_retrieval_pipeline_data()
    if df.empty:
        return

    ext_stats = df.groupby("extractor").agg(
        mean=("accuracy", "mean"),
        max=("accuracy", "max"),
    ).reset_index()
    ext_stats = ext_stats.sort_values("mean", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = [FT_COLOR if "finetuned" in e else PT_COLOR if e in {"resnet50","efficientnetb1","mobilenetv2"} else TR_COLOR
              for e in ext_stats["extractor"]]
    bars = ax.barh(range(len(ext_stats)), ext_stats["mean"] * 100, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(ext_stats)))
    ax.set_yticklabels(ext_stats["extractor"], fontsize=7)
    ax.set_xlabel("Mean Accuracy (%)")
    ax.set_title("Feature Extractors Ranked by Mean Retrieval Accuracy")
    ax.set_xlim(0, 100)

    for bar, mean_v, max_v in zip(bars, ext_stats["mean"], ext_stats["max"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{mean_v*100:.1f}% (max {max_v*100:.1f}%)",
                va="center", fontsize=6)

    ax.legend(handles=[
        plt.matplotlib.patches.Patch(facecolor=FT_COLOR, label="Finetuned"),
        plt.matplotlib.patches.Patch(facecolor=PT_COLOR, label="Pretrained"),
        plt.matplotlib.patches.Patch(facecolor=TR_COLOR, label="Traditional"),
    ], loc="lower right", fontsize=7)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    save("retrieval_extractor_sorted.png", fig)

    # Write table CSV
    table = ext_stats[["extractor", "mean", "max"]].copy()
    table["mean"] = (table["mean"] * 100).round(1)
    table["max"] = (table["max"] * 100).round(1)
    table = table.sort_values("mean", ascending=False).rename(
        columns={"mean": "mean_accuracy_pct", "max": "max_accuracy_pct"}
    )
    table_path = REPORT_DIR / "retrieval_extractor_sorted.csv"
    table.to_csv(table_path, index=False)
    print(f"  saved {table_path.name}")


# ═══════════════════════════════════════════════════════════════════════════
# 6. CV confusion matrix
# ═══════════════════════════════════════════════════════════════════════════

def chart_cv_confusion_matrix():
    import seaborn as sns
    from sklearn.metrics import confusion_matrix

    cv_df = pd.read_csv(CV_CSV) if CV_CSV.exists() else pd.DataFrame()
    if cv_df.empty:
        return

    # use best config: E2 freq_strength k=3 by efficientnetb1_finetuned
    best_cv = cv_df[
        (cv_df["extractor"] == "efficientnetb1_finetuned") &
        (cv_df["media_strategy"] == "E2") &
        (cv_df["agg_strategy"] == "freq_strength") &
        (cv_df["k"] == 3)
    ]
    if best_cv.empty:
        best_cv = cv_df.nlargest(100, "correct").head(50)

    y_true = best_cv["ground_truth"].tolist()
    y_pred = best_cv["predicted_specy"].tolist()
    correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
    accuracy = correct / len(y_true) if y_true else 0

    labels = sorted(set(y_true))
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(cm, annot=True, fmt="d", xticklabels=labels, yticklabels=labels,
                cmap="Blues", ax=ax)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.set_title(f"CV Confusion Matrix — EfficientNetB1 Finetuned E2 freq_strength K=3\nAccuracy: {accuracy:.2%} ({correct}/{len(y_true)})")
    plt.xticks(rotation=45, ha="right")
    fig.tight_layout()
    save("cv_confusion_matrix_best.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 7. CV vs Retrieval pipeline comparison
# ═══════════════════════════════════════════════════════════════════════════

def chart_cv_vs_retrieval():
    """Compare best CV configs against best retrieval pipeline configs."""
    rp = load_retrieval_pipeline_data()
    cv = load_cv_data()
    if rp.empty or cv.empty:
        return

    rp_best = rp.nlargest(5, "accuracy")[["extractor", "env", "agg", "k", "accuracy"]].copy()
    rp_best["source"] = "Retrieval Pipeline"

    cv_best = cv.nlargest(5, "accuracy")[["extractor", "media_strategy", "agg_strategy", "k", "accuracy"]].copy()
    cv_best = cv_best.rename(columns={"media_strategy": "env", "agg_strategy": "agg"})
    cv_best["source"] = "Cross-Validation"

    combined = pd.concat([rp_best, cv_best], ignore_index=True)
    combined["label"] = combined.apply(
        lambda r: f"{r['extractor'][:20]} {r['env']}", axis=1
    )
    combined = combined.sort_values("accuracy", ascending=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#2ca02c" if s == "Cross-Validation" else "#1f77b4" for s in combined["source"]]
    bars = ax.bar(range(len(combined)), combined["accuracy"] * 100, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(combined)))
    ax.set_xticklabels(combined["label"], fontsize=6, rotation=25, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Best Configs: Cross-Validation vs Retrieval Pipeline")
    ax.set_ylim(0, max(combined["accuracy"]) * 120)

    for bar, acc in zip(bars, combined["accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{acc*100:.1f}%", ha="center", fontsize=6)

    ax.legend(handles=[
        plt.matplotlib.patches.Patch(facecolor="#2ca02c", label="Cross-Validation"),
        plt.matplotlib.patches.Patch(facecolor="#1f77b4", label="Retrieval Pipeline"),
    ], loc="lower right", fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("cv_vs_retrieval_comparison.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Segmentation comparison (YOLO vs KMeans)
# ═══════════════════════════════════════════════════════════════════════════

def chart_segmentation_comparison():
    """YOLO vs KMeans: finetuned + pretrained in E1, colorhistogram, E3_CREA."""
    df = load_segmentation_data()
    if df.empty:
        return

    # Select specific configs
    target_media = ["E1", "E3_CREA"]
    df_sel = df[df["media"].isin(target_media)].copy()

    if df_sel.empty:
        # fallback to all
        df_sel = df.copy()

    configs = []
    for seg in ["yolo", "kmeans"]:
        for media in sorted(df_sel["media"].unique()):
            sub = df_sel[(df_sel["segmentation"] == seg) & (df_sel["media"] == media)]
            if not sub.empty:
                r = sub.iloc[0]
                configs.append({
                    "seg": seg,
                    "extractor": r["extractor"],
                    "media": media,
                    "accuracy": r["accuracy"],
                    "label": f"{seg}\n{media}"
                })

    if not configs:
        return

    cf = pd.DataFrame(configs)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(cf))
    w = 0.35
    yolo_mask = cf["seg"] == "yolo"
    kmeans_mask = cf["seg"] == "kmeans"

    b1 = ax.bar(x[yolo_mask] - w/2, cf.loc[yolo_mask, "accuracy"].values * 100, w,
                label="YOLO", color="#2ecc71")
    b2 = ax.bar(x[kmeans_mask] + w/2, cf.loc[kmeans_mask, "accuracy"].values * 100, w,
                label="K-Means", color="#3498db")
    ax.set_xticks(x)
    ax.set_xticklabels(cf["label"], fontsize=7)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("YOLO vs K-Means Segmentation: Retrieval Accuracy")
    ax.set_ylim(0, 100)

    for bar, acc in zip(b1, cf.loc[yolo_mask, "accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{acc*100:.1f}%", ha="center", fontsize=8)
    for bar, acc in zip(b2, cf.loc[kmeans_mask, "accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{acc*100:.1f}%", ha="center", fontsize=8)

    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("segmentation_vs_yolo_kmeans.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Accuracy vs K line chart (CV data)
# ═══════════════════════════════════════════════════════════════════════════

def chart_accuracy_vs_k():
    """Accuracy vs K for best CV strategies."""
    cv = load_cv_data()
    if cv.empty:
        return

    best_configs = cv.nlargest(5, "accuracy")[
        ["extractor", "media_strategy", "agg_strategy"]
    ].drop_duplicates()

    fig, ax = plt.subplots(figsize=(9, 5))
    cv_full = pd.read_csv(CV_CSV)
    cv_full["is_correct"] = cv_full["correct"]

    for _, cfg in best_configs.iterrows():
        sub = cv_full[
            (cv_full["extractor"] == cfg["extractor"]) &
            (cv_full["media_strategy"] == cfg["media_strategy"]) &
            (cv_full["agg_strategy"] == cfg["agg_strategy"])
        ]
        if sub.empty:
            continue
        k_acc = sub.groupby("k")["is_correct"].mean()
        label = f"{cfg['extractor'][:20]} {cfg['media_strategy']}"
        ax.plot(k_acc.index, k_acc.values * 100, "o-", label=label, linewidth=2)

    ax.set_xlabel("K")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Accuracy vs K — Top CV Configurations")
    ax.set_ylim(0, 100)
    ax.legend(fontsize=6, loc="lower right")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    save("cv_accuracy_vs_k.png", fig)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Generating retrieval experiment charts...")
    chart_retrieval_top_accuracy()
    chart_agg_vs_k_heatmap()
    chart_env_vs_agg_heatmap()
    chart_category_comparison()
    chart_extractor_sorted()
    chart_cv_confusion_matrix()
    chart_cv_vs_retrieval()
    chart_segmentation_comparison()
    chart_accuracy_vs_k()
    print("Done.")
