"""
EDA report for the incoming_low_quality (new_data) dataset used in threshold experiments.

Generates:
1. Species diversity comparison (curated vs incoming)
2. Strain scarcity analysis (strains per species)
3. Environment distribution
4. Sample image grid from new_data
5. YOLO bbox visualization on sample segmented images

Usage:
    uv run python -m src.experiments.threshold.new_data_eda_report
"""

from __future__ import annotations

import json
import random
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

from src.config import (
    CURATED_METADATA_PATH,
    INCOMING_METADATA_PATH,
    NEW_DATA_PREPARED_DATASET_DIR,
    WORKSPACE_ROOT,
)

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent.parent / "report" / "eda_new_data"
IMAGES_OUT = OUTPUT_DIR / "images"
REPORT_FIGURES = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/content/figures")
SEED = 42

FONT_TITLE = 14
FONT_LABEL = 12
FONT_TICK = 10


def _load_metadata(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def _compute_stats(metadata: list[dict]) -> dict:
    species = Counter()
    strains = Counter()
    envs = Counter()
    sp_strains = defaultdict(set)

    for img in metadata:
        info = img["instance_info"]
        species[info["species"]] += 1
        strains[info["strain"]] += 1
        envs[info["environment"]] += 1
        sp_strains[info["species"]].add(info["strain"])

    sp_strain_counts = {k: len(v) for k, v in sp_strains.items()}
    return {
        "species": species,
        "strains": strains,
        "envs": envs,
        "sp_strains": sp_strain_counts,
        "total_images": len(metadata),
        "n_species": len(species),
        "n_strains": len(strains),
        "n_envs": len(envs),
        "avg_strains_per_species": sum(sp_strain_counts.values()) / max(1, len(sp_strain_counts)),
        "avg_images_per_species": len(metadata) / max(1, len(species)),
    }


def _save_fig(fig: plt.Figure, name: str) -> Path:
    path = IMAGES_OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    report_path = REPORT_FIGURES / name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, report_path)

    return path


def plot_species_comparison(curated: dict, incoming: dict) -> Path:
    """Side-by-side bar chart: species count, images, avg strains/species."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    metrics = ["n_species", "total_images", "avg_strains_per_species"]
    labels = ["Species Count", "Total Images", "Avg Strains per Species"]
    curated_vals = [curated[m] for m in metrics]
    incoming_vals = [incoming[m] for m in metrics]

    x = np.arange(len(labels))
    width = 0.35

    for i, ax in enumerate(axes):
        bars1 = ax.bar(x[i] - width / 2, curated_vals[i], width, label="Curated (original)", color="#2ca02c")
        bars2 = ax.bar(x[i] + width / 2, incoming_vals[i], width, label="Incoming (new_data)", color="#d62728")
        ax.set_ylabel(labels[i])
        ax.set_xticks([x[i]])
        ax.set_xticklabels([labels[i]])

        for bar, val in zip(bars1, [curated_vals[i]]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(curated_vals[i], incoming_vals[i]) * 0.01,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=FONT_TICK, fontweight="bold")
        for bar, val in zip(bars2, [incoming_vals[i]]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(curated_vals[i], incoming_vals[i]) * 0.01,
                    f"{val:.1f}", ha="center", va="bottom", fontsize=FONT_TICK, fontweight="bold")

        if i == 0:
            ax.legend(fontsize=9)

    fig.suptitle("Curated vs Incoming Dataset Comparison", fontsize=FONT_TITLE, fontweight="bold")
    fig.tight_layout()
    return _save_fig(fig, "eda_new_comparison_overview.png")


def plot_strains_per_species_distribution(curated_sp_strains: dict, incoming_sp_strains: dict) -> Path:
    """Histogram: how many species have 1, 2, 3, ... strains."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    for ax, sp_strains, title, color in [
        (axes[0], incoming_sp_strains, "Incoming (new_data) — 46 species", "#d62728"),
        (axes[1], curated_sp_strains, "Curated (original) — 8 species", "#2ca02c"),
    ]:
        dist = Counter(sp_strains.values())
        max_n = max(dist.keys()) if dist else 1
        values = [dist.get(i, 0) for i in range(1, max_n + 1)]
        x_pos = np.arange(1, max_n + 1)

        bars = ax.bar(x_pos, values, width=0.6, color=color, edgecolor="white", linewidth=0.5)
        ax.set_xticks(x_pos)
        ax.set_xlabel("Strains per Species", fontsize=FONT_LABEL)
        ax.set_ylabel("Number of Species", fontsize=FONT_LABEL)
        ax.set_title(title, fontsize=FONT_LABEL, fontweight="bold")
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.02,
                    str(val), ha="center", fontsize=FONT_TICK, fontweight="bold")

    fig.suptitle("Strains-per-Species Distribution", fontsize=FONT_TITLE, fontweight="bold")
    fig.tight_layout()
    return _save_fig(fig, "eda_new_strains_per_species.png")


def plot_incoming_species_top(incoming: dict) -> Path:
    """Horizontal bar chart of top species by image count in incoming."""
    species = incoming["species"]
    sorted_items = sorted(species.items(), key=lambda x: x[1], reverse=True)[:20]
    labels, values = zip(*sorted_items) if sorted_items else ([], [])

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.RdYlGn_r(np.linspace(0.15, 0.9, len(labels)))
    bars = ax.barh(range(len(labels)), values, color=colors, edgecolor="white")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Image Count", fontsize=FONT_LABEL)
    ax.set_title("Top 20 Species by Image Count — Incoming (new_data)", fontsize=FONT_TITLE, fontweight="bold")
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9)

    fig.tight_layout()
    return _save_fig(fig, "eda_new_incoming_species_top20.png")


def plot_incoming_environments(incoming: dict) -> Path:
    """Bar chart of environment distribution."""
    envs = incoming["envs"]
    sorted_items = sorted(envs.items(), key=lambda x: x[1], reverse=True)
    labels, values = zip(*sorted_items)

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))
    bars = ax.bar(range(len(labels)), values, color=colors, edgecolor="white")
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=FONT_TICK)
    ax.set_ylabel("Image Count", fontsize=FONT_LABEL)
    ax.set_title("Environment Distribution — Incoming (new_data)", fontsize=FONT_TITLE, fontweight="bold")
    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(values) * 0.01,
                str(val), ha="center", fontsize=FONT_TICK, fontweight="bold")

    fig.tight_layout()
    return _save_fig(fig, "eda_new_incoming_environments.png")


def plot_sample_image_grid(incoming_meta: list[dict]) -> Optional[Path]:
    """Grid of sample segmented colony images from new_data, organized by environment."""
    import cv2

    # Group by environment, pick first species
    random.seed(SEED)
    env_groups = defaultdict(list)
    for img in incoming_meta:
        info = img["instance_info"]
        sp = info["species"]
        seg_paths = img.get("paths", {}).get("segments", [])
        if seg_paths:
            for spath in seg_paths:
                resolved = WORKSPACE_ROOT / spath
                if resolved.exists():
                    env_groups[info["environment"]].append((resolved, sp, info["strain"]))

    envs = sorted(env_groups.keys())
    envs = [e for e in envs if e not in ("UNKNOWN", "OA")][:5]

    n_envs = len(envs)
    n_cols = 4
    n_rows = n_envs

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(12, n_rows * 3))
    if n_rows == 1:
        axes = np.array([axes])

    for row, env in enumerate(envs):
        samples = random.sample(env_groups[env], min(n_cols, len(env_groups[env])))
        for col in range(n_cols):
            ax = axes[row, col]
            if col < len(samples):
                img_path, sp, strain = samples[col]
                img = cv2.imread(str(img_path))
                if img is not None:
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                    ax.imshow(img)
                    ax.set_title(f"{sp}\n{strain}", fontsize=7)
                else:
                    ax.text(0.5, 0.5, "Load err", ha="center", va="center", fontsize=7)
            else:
                ax.axis("off")
            ax.set_xticks([])
            ax.set_yticks([])

        axes[row, 0].set_ylabel(env, fontsize=FONT_LABEL, fontweight="bold", rotation=0, labelpad=40)

    fig.suptitle("Sample Segmented Colonies — Incoming (new_data) by Environment",
                 fontsize=FONT_TITLE, fontweight="bold")
    fig.tight_layout()
    return _save_fig(fig, "eda_new_sample_images.png")


def plot_yolo_bbox_demo() -> Optional[Path]:
    """Use existing new_data_prepared YOLO26 artifacts for qualitative bbox visualization."""
    import cv2

    bbox_paths = sorted(NEW_DATA_PREPARED_DATASET_DIR.glob("*/*/*/*/bbox_yolo.jpg"))
    if not bbox_paths:
        print("WARNING: no bbox_yolo.jpg files found in new_data_prepared")
        return None

    random.seed(SEED)
    selected = random.sample(bbox_paths, min(6, len(bbox_paths)))

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    axes = axes.flatten()

    for i, bbox_path in enumerate(selected):
        ax = axes[i]
        img = cv2.imread(str(bbox_path))
        if img is None:
            ax.text(0.5, 0.5, "Load err", ha="center", va="center")
            continue

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        species, strain, env, angle = bbox_path.parts[-5:-1]

        ax.imshow(img)
        ax.set_title(f"{species} | {strain}\n{env} | {angle}", fontsize=8)
        ax.set_xticks([])
        ax.set_yticks([])

    for j in range(len(selected), len(axes)):
        axes[j].axis("off")

    fig.suptitle("YOLO26 Fine-tuned Bounding Boxes on new_data_prepared Images",
                 fontsize=FONT_TITLE, fontweight="bold")
    fig.tight_layout()
    return _save_fig(fig, "eda_new_yolo_bbox_demo.png")


def plot_species_diversity_radar(curated: dict, incoming: dict) -> Path:
    """Radar-like side-by-side table showing the diversity contrast."""
    fig, ax = plt.subplots(figsize=(10, 2.5))
    ax.axis("off")

    col_labels = ["Metric", "Curated (original)", "Incoming (new_data)", "Ratio"]
    rows = [
        ["Species", str(curated["n_species"]), str(incoming["n_species"]),
         f"{incoming['n_species'] / max(1, curated['n_species']):.1f}x"],
        ["Strains", str(curated["n_strains"]), str(incoming["n_strains"]),
         f"{incoming['n_strains'] / max(1, curated['n_strains']):.1f}x"],
        ["Images", str(curated["total_images"]), str(incoming["total_images"]),
         f"{incoming['total_images'] / max(1, curated['total_images']):.2f}x"],
        ["Avg Strains/Species", f"{curated['avg_strains_per_species']:.1f}",
         f"{incoming['avg_strains_per_species']:.1f}",
         f"{curated['avg_strains_per_species'] / max(0.1, incoming['avg_strains_per_species']):.1f}x"],
        ["Avg Images/Species", f"{curated['avg_images_per_species']:.1f}",
         f"{incoming['avg_images_per_species']:.1f}",
         f"{curated['avg_images_per_species'] / max(0.1, incoming['avg_images_per_species']):.1f}x"],
        ["1-Strain Species", str(sum(1 for v in curated["sp_strains"].values() if v == 1)),
         str(sum(1 for v in incoming["sp_strains"].values() if v == 1)),
         ""],
    ]

    table = ax.table(cellText=rows, colLabels=col_labels, cellLoc="center", loc="center",
                     colColours=["#e8e8e8"] * 4)

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.0, 1.6)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#404040")
            cell.set_text_props(color="white", fontweight="bold")
        elif col == 0:
            cell.set_facecolor("#f0f0f0")
            cell.set_text_props(fontweight="bold")
        elif col == 1:
            cell.set_facecolor("#e8f5e9")
        elif col == 2:
            cell.set_facecolor("#fce4ec")
        elif col == 3:
            cell.set_facecolor("#fff8e1")

    ax.set_title("Key Dataset Diversity Metrics: Curated vs Incoming",
                 fontsize=FONT_TITLE, fontweight="bold", pad=20)
    fig.tight_layout()
    return _save_fig(fig, "eda_new_diversity_table.png")


def main() -> None:
    IMAGES_OUT.mkdir(parents=True, exist_ok=True)
    random.seed(SEED)
    np.random.seed(SEED)

    print("Loading metadata...")
    curated_meta = _load_metadata(CURATED_METADATA_PATH)
    incoming_meta = _load_metadata(INCOMING_METADATA_PATH)

    print(f"  Curated: {len(curated_meta)} images")
    print(f"  Incoming: {len(incoming_meta)} images")

    curated_stats = _compute_stats(curated_meta)
    incoming_stats = _compute_stats(incoming_meta)

    print(f"\nCurated: {curated_stats['n_species']} species, {curated_stats['n_strains']} strains, "
          f"{curated_stats['avg_strains_per_species']:.1f} avg strains/species")
    print(f"Incoming: {incoming_stats['n_species']} species, {incoming_stats['n_strains']} strains, "
          f"{incoming_stats['avg_strains_per_species']:.1f} avg strains/species")

    print(f"\nIncoming 1-strain species: "
          f"{sum(1 for v in incoming_stats['sp_strains'].values() if v == 1)} / {incoming_stats['n_species']}")

    print("\nGenerating charts...")

    r = plot_species_comparison(curated_stats, incoming_stats)
    print(f"  [1/7] Species comparison → {r}")

    r = plot_strains_per_species_distribution(
        curated_stats["sp_strains"], incoming_stats["sp_strains"]
    )
    print(f"  [2/7] Strains-per-species distribution → {r}")

    r = plot_incoming_species_top(incoming_stats)
    print(f"  [3/7] Top species (incoming) → {r}")

    r = plot_incoming_environments(incoming_stats)
    print(f"  [4/7] Environment distribution → {r}")

    r = plot_species_diversity_radar(curated_stats, incoming_stats)
    print(f"  [5/7] Diversity table → {r}")

    r = plot_sample_image_grid(incoming_meta)
    if r:
        print(f"  [6/7] Sample image grid → {r}")
    else:
        print("  [6/7] Sample image grid → SKIPPED (no segment images)")

    r = plot_yolo_bbox_demo()
    if r:
        print(f"  [7/7] YOLO bbox demo → {r}")
    else:
        print("  [7/7] YOLO bbox demo → SKIPPED (no model)")

    print(f"\nDone! Figures in {IMAGES_OUT}")
    print(f"Also copied to {REPORT_FIGURES}")


if __name__ == "__main__":
    main()
