"""Refresh all graduation report charts from latest experiment results.

Collects data from the canonical retrieval, threshold, and cross-validation
outputs and regenerates every figure used in the thesis report.
"""
from pathlib import Path
import json, csv, shutil
from collections import Counter, defaultdict

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

RETRIEVAL_LATEST = PROJECT / "results/retrieval_k7_yolo_finalcheck"
RETRIEVAL_K3 = PROJECT / "results/retrieval_20260629_192407"
RETRIEVAL_KMEANS = PROJECT / "results/retrieval_k7_kmeans_local"
RETRIEVAL_K7_ALL = PROJECT / "results/retrieval_k7_all"
THRESH_CSV = PROJECT / "results/threshold/log/all_experiments.csv"
THRESH_SUMMARY = PROJECT / "results/threshold/metric_analysis.json"
CV_SUMMARY = PROJECT / "results/cross_validation/cv_summary_table.csv"

FT_BLUE = "#1f77b4"
PT_ORANGE = "#ff7f0e"
TRAD_GREEN = "#2ca02c"
YOLO_GREEN = "#2ecc71"
KMEANS_BLUE = "#3498db"


def save(name, fig=None, subfolder=None):
    if fig is None:
        return
    sf = subfolder + "/" if subfolder else ""
    for out in (LATEX_DIR / sf / name, REPORT_DIR / sf / name):
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved {sf}{name}")


def copy_img(src, dst_name, subfolder=None):
    src = Path(src) if isinstance(src, str) else src
    if src.exists():
        sf = subfolder + "/" if subfolder else ""
        for out in (LATEX_DIR / sf / dst_name, REPORT_DIR / sf / dst_name):
            shutil.copy2(src, out)
        print(f"  copied {dst_name}")


def load_accuracies(base_dir):
    rows = []
    if not base_dir.exists():
        return rows
    for d in base_dir.iterdir():
        if not d.is_dir():
            continue
        jf = d / "evaluation_results.json"
        if not jf.exists():
            continue
        data = json.loads(jf.read_text())
        rows.append({
            "dir": d.name,
            "accuracy": data["overall_accuracy"],
            "correct": data.get("correct_predictions", 0),
            "total": data.get("total_strains", 0),
        })
    return rows


# ═══════════════════════════════════════════════════════════════════════════
# 1. Extractor comparison bar chart (freq_strength, E1, K=7)
# ═══════════════════════════════════════════════════════════════════════════
def chart_extractor_comparison():
    all_rows = load_accuracies(RETRIEVAL_K7_ALL)
    if not all_rows:
        yolo_rows = load_accuracies(RETRIEVAL_LATEST)
        km_rows = load_accuracies(RETRIEVAL_KMEANS)
        if not yolo_rows and not km_rows:
            return
        all_rows = yolo_rows + km_rows

    exact = [
        ("efficientnetb1_finetuned_7_freq_strength_E1_yolo", "EfficientNetB1 (FT)", FT_BLUE, "YOLO"),
        ("mobilenetv2_finetuned_7_freq_strength_E1_yolo", "MobileNetV2 (FT)", FT_BLUE, "YOLO"),
        ("resnet50_finetuned_7_freq_strength_E1_yolo", "ResNet50 (FT)", FT_BLUE, "YOLO"),
        ("efficientnetb1_7_freq_strength_E1_yolo", "EfficientNetB1 (PT)", PT_ORANGE, "YOLO"),
        ("mobilenetv2_7_freq_strength_E1_yolo", "MobileNetV2 (PT)", PT_ORANGE, "YOLO"),
        ("resnet50_7_freq_strength_E1_yolo", "ResNet50 (PT)", PT_ORANGE, "YOLO"),
        ("colorhistogramhs_7_freq_strength_E1_kmeans", "ColorHist HS", TRAD_GREEN, "K-Means"),
        ("colorhistogram_7_freq_strength_E1_kmeans", "ColorHist HSV", TRAD_GREEN, "K-Means"),
        ("hog_7_freq_strength_E1_kmeans", "HOG", TRAD_GREEN, "K-Means"),
        ("gabor_7_freq_strength_E1_kmeans", "Gabor", TRAD_GREEN, "K-Means"),
    ]

    results = []
    for folder, label, color, segmenter in exact:
        match = next((r for r in all_rows if r["dir"] == folder), None)
        if match is not None:
            results.append((label, match["accuracy"] * 100, color, segmenter))

    if not results:
        return

    results.sort(key=lambda x: x[1], reverse=True)
    labels = [f"{label}\n({segmenter})" for label, _, _, segmenter in results]
    scores = [score for _, score, _, _ in results]
    colors = [color for _, _, color, _ in results]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    bars = ax.bar(range(len(labels)), scores, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7, rotation=25, ha="right")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Feature Extractor Comparison (freq_strength, E1, K=7)")
    ax.set_ylim(0, max(scores) * 1.2 if max(scores) > 0 else 100)
    for bar, score in zip(bars, scores):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                f"{score:.1f}%", ha="center", va="bottom", fontsize=7, fontweight="bold")
    ax.legend(handles=[
        plt.matplotlib.patches.Patch(facecolor=FT_BLUE, label="Fine-tuned DL"),
        plt.matplotlib.patches.Patch(facecolor=PT_ORANGE, label="Pretrained DL"),
        plt.matplotlib.patches.Patch(facecolor=TRAD_GREEN, label="Traditional"),
    ], loc="upper right", fontsize=7)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("extractor_comparison.png", fig, subfolder="06_retrieval")


# ═══════════════════════════════════════════════════════════════════════════
# 2. KMeans vs YOLO comparison
# ═══════════════════════════════════════════════════════════════════════════
def chart_kmeans_vs_yolo():
    yolo_rows = load_accuracies(RETRIEVAL_LATEST) if RETRIEVAL_LATEST.exists() else []
    km_rows = load_accuracies(RETRIEVAL_KMEANS) if RETRIEVAL_KMEANS.exists() else []
    pairs = [
        ("resnet50_7_weighted_E1_yolo", "resnet50_7_weighted_E1_kmeans"),
        ("resnet50_finetuned_7_weighted_E1_yolo", "resnet50_finetuned_7_weighted_E1_kmeans"),
    ]
    labels = ["ResNet50 (PT)", "ResNet50 (FT)"]
    yolo_vals = []
    km_vals = []
    for y_name, k_name in pairs:
        y = next((r["accuracy"] * 100 for r in yolo_rows if r["dir"] == y_name), 0.0)
        k = next((r["accuracy"] * 100 for r in km_rows if r["dir"] == k_name), 0.0)
        yolo_vals.append(y)
        km_vals.append(k)
    if max(yolo_vals + km_vals) == 0:
        return

    fig, ax = plt.subplots(figsize=(7, 4.5))
    x = range(len(labels))
    w = 0.35
    b1 = ax.bar([i - w / 2 for i in x], yolo_vals, w, label="YOLO segments", color=YOLO_GREEN)
    b2 = ax.bar([i + w / 2 for i in x], km_vals, w, label="K-Means segments", color=KMEANS_BLUE)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("YOLO vs K-Means: Retrieval Accuracy (ResNet50)")
    for b, v in zip(b1, yolo_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
    for b, v in zip(b2, km_vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.5, f"{v:.1f}", ha="center", fontsize=8)
    ax.set_ylim(0, max(yolo_vals + km_vals) * 1.2)
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("kmeans_vs_yolo_latest.png", fig, subfolder="06_retrieval")


# ═══════════════════════════════════════════════════════════════════════════
# 3. CV heatmaps
# ═══════════════════════════════════════════════════════════════════════════
def chart_cv_heatmaps():
    if not CV_SUMMARY.exists():
        return
    df = pd.read_csv(CV_SUMMARY)
    if df.empty:
        return

    df["mean_accuracy"] = df["mean_accuracy"] * 100
    media_col = "media_strategy" if "media_strategy" in df.columns else "env_strategy"
    agg_vals = sorted(df["agg_strategy"].unique())
    media_vals = sorted(df[media_col].unique())
    k_vals = sorted(df["k"].unique())

    for agg in agg_vals:
        subset = df[df["agg_strategy"] == agg]
        mat = np.zeros((len(media_vals), len(k_vals)))
        for i, m in enumerate(media_vals):
            for j, k in enumerate(k_vals):
                row = subset[(subset[media_col] == m) & (subset["k"] == k)]
                mat[i, j] = row["mean_accuracy"].mean() if not row.empty else 0
        if mat.max() == 0:
            continue
        fig, ax = plt.subplots(figsize=(6, 2.5))
        im = ax.imshow(mat, cmap="YlOrRd", aspect="auto", vmin=mat[mat > 0].min() * 0.95, vmax=mat.max() * 1.02)
        ax.set_xticks(range(len(k_vals)))
        ax.set_xticklabels([f"K={k}" for k in k_vals])
        ax.set_yticks(range(len(media_vals)))
        ax.set_yticklabels(media_vals, fontsize=7)
        for i in range(len(media_vals)):
            for j in range(len(k_vals)):
                v = mat[i, j]
                ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6,
                        color="black" if v < 75 else "white")
        ax.set_title(f"CV Accuracy: {agg} (mean across extracts)")
        plt.colorbar(im, ax=ax, label="Accuracy %")
        fig.tight_layout()
        save(f"cv_heatmap_{agg}.png", fig, subfolder="05_cross_validation")

    mat2 = np.zeros((len(agg_vals), len(k_vals)))
    for i, a in enumerate(agg_vals):
        for j, k in enumerate(k_vals):
            vs = df[(df["agg_strategy"] == a) & (df["k"] == k)]["mean_accuracy"]
            mat2[i, j] = vs.mean() if len(vs) else 0
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow(mat2, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(k_vals)))
    ax.set_xticklabels([f"K={k}" for k in k_vals])
    ax.set_yticks(range(len(agg_vals)))
    ax.set_yticklabels(agg_vals, fontsize=7)
    for i in range(len(agg_vals)):
        for j in range(len(k_vals)):
            ax.text(j, i, f"{mat2[i, j]:.1f}", ha="center", va="center", fontsize=6,
                    color="black" if mat2[i, j] < 75 else "white")
    ax.set_title("CV: Aggregation vs K")
    plt.colorbar(im, ax=ax, label="Accuracy %")
    fig.tight_layout()
    save("cv_heatmap_agg_vs_k.png", fig, subfolder="05_cross_validation")


# ═══════════════════════════════════════════════════════════════════════════
# 4. Threshold top strategies
# ═══════════════════════════════════════════════════════════════════════════
def chart_threshold_top():
    if not THRESH_CSV.exists():
        return
    df = pd.read_csv(THRESH_CSV)
    if df.empty or "f1" not in df.columns:
        return
    df = df[df["f1"] > 0]
    df["name"] = df["formula"] + "_" + df["algorithm"]
    top = df.nlargest(15, "f1")

    fig, ax = plt.subplots(figsize=(10, 5))
    colors_cmap = plt.cm.viridis(np.linspace(0, 1, len(top)))
    bars = ax.barh(range(len(top)), top["f1"].values, color=colors_cmap, edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels(top["name"].values, fontsize=6)
    ax.set_xlabel("F1 Score")
    ax.set_title("Top 15 Threshold Strategies by F1 Score")
    ax.invert_yaxis()
    for i, (v, p) in enumerate(zip(top["f1"], top["precision"] if "precision" in top.columns else [0] * len(top))):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=6)
    ax.set_xlim(0, max(top["f1"]) * 1.3)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    save("threshold_top_bar.png", fig, subfolder="07_threshold")


# ═══════════════════════════════════════════════════════════════════════════
# 5. Copy confusion matrices
# ═══════════════════════════════════════════════════════════════════════════
def copy_confusion_matrices():
    if RETRIEVAL_LATEST.exists():
        for cfg in ["resnet50_finetuned_7_weighted_E1_yolo",
                     "efficientnetb1_finetuned_7_weighted_E1_yolo",
                     "mobilenetv2_finetuned_7_weighted_E1_yolo",
                     "resnet50_7_weighted_E1_yolo"]:
            src = RETRIEVAL_LATEST / cfg / "confusion_matrix.png"
            if src.exists():
                fn = f"confusion_matrix_{cfg.split('_')[0]}.png"
                copy_img(src, fn, subfolder="06_retrieval")
    thresh_cm = PROJECT / "results/threshold/confusion_matrix_threshold.png"
    if thresh_cm.exists():
        copy_img(thresh_cm, "confusion_matrix_threshold.png", subfolder="06_retrieval")


# ═══════════════════════════════════════════════════════════════════════════
# 6. CV training curves (fold0 ResNet50 + EffB1)
# ═══════════════════════════════════════════════════════════════════════════
def chart_cv_training_curves():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for ax_idx, model in enumerate(["ResNet50", "EfficientNetB1"]):
        ax = axes[ax_idx]
        for fold in range(5):
            hp = PROJECT / "weights/folds" / f"fold{fold}_{model}_history.json"
            if not hp.exists():
                continue
            h = json.loads(hp.read_text())
            acc_key = "val_acc" if "val_acc" in h else "val_accuracy"
            ax.plot(h.get(acc_key, []), label=f"Fold {fold + 1}", linewidth=2, alpha=0.8)
        ax.set_xlabel("Epoch")
        ax.set_ylabel("Validation Accuracy")
        ax.set_title(f"{model} Fold-Specific Training")
        ax.legend(fontsize=7)
        ax.grid(alpha=0.3)
    fig.tight_layout()
    save("cv_training_curves_folds.png", fig, subfolder="05_cross_validation")


# ═══════════════════════════════════════════════════════════════════════════
# 7. Per-fold accuracy distribution
# ═══════════════════════════════════════════════════════════════════════════
def chart_fold_variance():
    cv_csv = PROJECT / "results/cross_validation/cv_results.csv"
    if not cv_csv.exists():
        return
    df = pd.read_csv(cv_csv)
    if df.empty:
        return
    target = df[
        (df["extractor"].astype(str).str.contains("efficientnetb1_finetuned", na=False))
        & (df["agg_strategy"] == "freq_strength")
        & (df["k"] == 3)
        & ((df.get("media_strategy", df.get("env_strategy")) == "E2") if "media_strategy" in df.columns or "env_strategy" in df.columns else True)
    ].copy()
    if target.empty:
        target = df[
            (df["extractor"].astype(str).str.contains("efficientnetb1_finetuned", na=False))
            & (df["agg_strategy"] == "freq_strength")
        ].copy()
    if target.empty:
        target = df.copy()
    fold_means = target.groupby("fold")["correct"].mean()
    if len(fold_means) == 0:
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"]
    ax.bar(fold_means.index, fold_means.values * 100, color=colors[:len(fold_means)])
    for f, acc in fold_means.items():
        ax.text(f, acc * 100 + 0.5, f"{acc:.1%}", ha="center")
    ax.set_xlabel("Fold")
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Per-Fold Retrieval Accuracy (best fold-specific CV setting)")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("fold_variance_new.png", fig, subfolder="08_training")


# ═══════════════════════════════════════════════════════════════════════════
# 9. EDA media distribution (with CYA normalization)
# ═══════════════════════════════════════════════════════════════════════════
def chart_eda_media_distribution():
    """Regenerate media distribution charts using normalized environment labels."""
    import sys
    sys.path.insert(0, str(PROJECT / "research"))
    from src.prepare.dataset import (
        load_source_collections,
        iter_source_images,
        load_strain_species_mapping,
        normalize_label,
        parse_curated_metadata,
        parse_incoming_metadata,
    )

    collections = load_source_collections()
    strain_species_mapping = load_strain_species_mapping()
    env_counts: Counter = Counter()

    for key in ["curated"]:
        for image_path in iter_source_images(collections[key]):
            metadata = parse_curated_metadata(image_path, strain_species_mapping)
            env_counts[metadata.environment] += 1

    filtered = {k: v for k, v in sorted(env_counts.items()) if k != "unknown"}
    labels = list(filtered.keys())
    values = list(filtered.values())
    total = sum(values)

    colors = ["#1f77b4" if l == "CYA" else "#ff7f0e" for l in labels]

    for filename in ["eda_media_distribution.png"]:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5)
        ax.set_ylabel("Number of Images")
        ax.set_title("Media Distribution — Curated Dataset")
        ax.set_ylim(0, max(values) * 1.25)

        for bar, val in zip(bars, values):
            pct = val / total * 100
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 2,
                f"{val}\n({pct:.1f}%)",
                ha="center", va="bottom", fontsize=8,
            )

        note = "CYA includes CYA30 and CYAS variants"
        ax.text(0.5, -0.12, note, transform=ax.transAxes, fontsize=7, ha="center",
                va="top", style="italic", color="gray")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        save(filename, fig, subfolder="04_eda")

    # ── EDA media × species heatmap ──
    species_env: Counter = Counter()
    for key in ["curated"]:
        for image_path in iter_source_images(collections[key]):
            metadata = parse_curated_metadata(image_path, strain_species_mapping)
            if (
                metadata.species != "unknown"
                and metadata.environment != "unknown"
            ):
                species_env[(metadata.species, metadata.environment)] += 1

    environments = sorted({e for (_, e) in species_env})
    species = sorted({s for (s, _) in species_env})
    n_rows = min(len(species), 25)
    top_names = sorted(species, key=lambda s: -sum(
        species_env.get((s, e), 0) for e in environments
    ))[:n_rows]

    mat = np.zeros((len(top_names), len(environments)))
    for i, sp in enumerate(top_names):
        for j, env in enumerate(environments):
            mat[i, j] = species_env.get((sp, env), 0)

    fig, ax = plt.subplots(figsize=(8, 8))
    im = ax.imshow(mat, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(environments)))
    ax.set_xticklabels(environments, fontsize=7, rotation=45, ha="right")
    ax.set_yticks(range(len(top_names)))
    ax.set_yticklabels([n[:30] for n in top_names], fontsize=6)
    ax.set_title("Species x Media Distribution (CYA variants normalized)")
    for i in range(len(top_names)):
        for j in range(len(environments)):
            val = mat[i, j]
            if val > 0:
                ax.text(j, i, str(int(val)), ha="center", va="center",
                        fontsize=7, fontweight="bold",
                        color="white" if val > mat.max() / 2 else "black")
    plt.colorbar(im, ax=ax, label="Images")
    fig.tight_layout()
    save("eda_media_species_heatmap.png", fig, subfolder="04_eda")

    # ── EDA media vs other bar ──
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_ylabel("Number of Images")
    ax.set_title("Media Distribution — Curated Dataset")
    ax.set_ylim(0, max(values) * 1.25)
    for bar, val in zip(bars, values):
        pct = val / total * 100
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 2,
            f"{val}\n({pct:.1f}%)",
            ha="center", va="bottom", fontsize=8,
        )
    note = "CYA includes CYA30 and CYAS variants"
    ax.text(0.5, -0.12, note, transform=ax.transAxes, fontsize=7, ha="center",
            va="top", style="italic", color="gray")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    save("eda_media_vs_other.png", fig, subfolder="04_eda")

    print(f"  eda media: {dict(sorted(env_counts.items()))}")


# ═══════════════════════════════════════════════════════════════════════════
# 10. EDA curated-only charts (species distribution, strain distribution, few-shot scatter)
# ═══════════════════════════════════════════════════════════════════════════
def chart_eda_curated():
    """Regenerate EDA charts using only the curated dataset."""
    import sys
    sys.path.insert(0, str(PROJECT / "research"))
    from src.prepare.dataset import (
        load_source_collections,
        iter_source_images,
        load_strain_species_mapping,
        parse_curated_metadata,
    )

    collections = load_source_collections()
    strain_species_mapping = load_strain_species_mapping()
    species_counts: Counter = Counter()
    strain_species: dict[str, str] = {}  # strain -> species
    strain_img_counts: Counter = Counter()

    for image_path in iter_source_images(collections["curated"]):
        metadata = parse_curated_metadata(image_path, strain_species_mapping)
        species_counts[metadata.species] += 1
        strain_species[metadata.strain] = metadata.species
        strain_img_counts[metadata.strain] += 1

    # ── Species distribution (horizontal bar) ──
    sorted_species = sorted(species_counts.items(), key=lambda x: -x[1])
    sp_names = [s for s, _ in sorted_species]
    sp_vals = [v for _, v in sorted_species]
    fig, ax = plt.subplots(figsize=(9, 4))
    bars = ax.barh(range(len(sp_names)), sp_vals[::-1], color="#1f77b4", edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(sp_names)))
    ax.set_yticklabels(sp_names[::-1], fontsize=8)
    ax.set_xlabel("Number of Dish Images")
    ax.set_title("Species Distribution — Curated Dataset")
    for bar, val in zip(bars, sp_vals[::-1]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=8)
    ax.set_xlim(0, max(sp_vals) * 1.15)
    fig.tight_layout()
    save("eda_species_distribution.png", fig, subfolder="04_eda")

    # ── Strain distribution (per-species colour) ──
    sorted_strains = sorted(strain_img_counts.items(), key=lambda x: -x[1])
    st_names = [s for s, _ in sorted_strains]
    st_vals = [v for _, v in sorted_strains]
    st_species = [strain_species.get(s, "unknown") for s in st_names]
    unique_species = sorted(set(st_species))
    palette = plt.cm.tab10.colors
    sp_color = {sp: palette[i % 10] for i, sp in enumerate(unique_species)}

    fig, ax = plt.subplots(figsize=(12, 4.5))
    colors = [sp_color[sp] for sp in st_species]
    bars = ax.bar(range(len(st_names)), st_vals, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xticks(range(len(st_names)))
    ax.set_xticklabels(st_names, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Number of Images")
    ax.set_title("Images per Strain — Curated Dataset")
    for bar, val in zip(bars, st_vals):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                str(val), ha="center", va="bottom", fontsize=7)
    handles = [plt.Rectangle((0, 0), 1, 1, color=sp_color[sp]) for sp in unique_species]
    ax.legend(handles, unique_species, fontsize=6, loc="upper right")
    ax.set_ylim(0, max(st_vals) * 1.2)
    fig.tight_layout()
    save("eda_strain_distribution.png", fig, subfolder="04_eda")

    # ── Few-shot scatter (species: strains vs images) ──
    sp_strain_count = Counter()
    sp_image_count = Counter()
    for strain, sp in strain_species.items():
        sp_strain_count[sp] += 1
    for sp, cnt in species_counts.items():
        sp_image_count[sp] = cnt

    sp_list = sorted(species_counts.keys())
    x_vals = [sp_strain_count.get(sp, 0) for sp in sp_list]
    y_vals = [sp_image_count.get(sp, 0) for sp in sp_list]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(x_vals, y_vals, c="#1f77b4", s=200, edgecolors="white", linewidth=0.8, zorder=3)
    for sp, x, y in zip(sp_list, x_vals, y_vals):
        short = sp.replace("Penicillium ", "P. ")
        ax.annotate(short, (x, y), textcoords="offset points", xytext=(5, 5), fontsize=8)
    ax.set_xlabel("Number of Strains")
    ax.set_ylabel("Number of Dish Images")
    ax.set_title("Few-Shot Classification Challenge — Curated Dataset")
    ax.set_xlim(-0.5, max(x_vals) + 1.5)
    ax.set_ylim(-5, max(y_vals) + 15)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    save("eda_fewshot_scatter.png", fig, subfolder="04_eda")

    print(f"  eda curated: {len(species_counts)} species, {len(strain_img_counts)} strains, {sum(species_counts.values())} images")


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Generating graduation report charts...")
    chart_extractor_comparison()
    chart_kmeans_vs_yolo()
    chart_cv_heatmaps()
    chart_threshold_top()
    chart_cv_training_curves()
    copy_confusion_matrices()
    chart_fold_variance()
    chart_eda_media_distribution()
    chart_eda_curated()
    print("Done.")
