"""
Generate score distribution charts for threshold experiment results.
- s0_score histogram: known vs unknown
- Top-3 geometric mean histogram: known vs unknown
- Box plot of s0_score by top 10 species
- s0 vs top3_gmean scatter (known only, colored by correct/wrong)
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.config import RESULTS_DIR

CSV_PATH = RESULTS_DIR / "threshold" / "diverse_retrieval_results.csv"
OUTPUT_DIR = RESULTS_DIR / "threshold"


def _strip_penicillium(label: str) -> str:
    clean = str(label).strip().lower()
    for prefix in ("penicillium ",):
        if clean.startswith(prefix):
            return clean[len(prefix):]
    return clean


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    known_mask = df["is_known"] == 1
    unknown_mask = df["is_known"] == 0
    known = df[known_mask]
    unknown = df[unknown_mask]

    df["s0"] = df["s0_score"].astype(float)
    df["s1"] = df["s1_score"].astype(float)
    df["s2"] = df["s2_score"].astype(float)
    df["top3_gmean"] = stats.gmean(
        df[["s0", "s1", "s2"]].clip(lower=1e-10), axis=1
    )

    known["s0"] = known["s0_score"].astype(float)
    unknown["s0"] = unknown["s0_score"].astype(float)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Threshold Experiment — Score Distributions", fontsize=16, fontweight="bold")

    # --- Plot 1: s0_score histogram known vs unknown ---
    ax1 = axes[0, 0]
    bins = np.linspace(0, 1.1, 50)
    ax1.hist(known["s0"], bins=bins, alpha=0.7, label=f"Known (n={len(known)})", color="steelblue", edgecolor="white")
    ax1.hist(unknown["s0"], bins=bins, alpha=0.7, label=f"Unknown (n={len(unknown)})", color="coral", edgecolor="white")
    ax1.set_xlabel("s0 Score (Top Prediction Confidence)")
    ax1.set_ylabel("Count")
    ax1.set_title("s0 Score Distribution: Known vs Unknown")
    ax1.legend(fontsize=8)
    ax1.set_xlim(0, 1.1)
    ax1.grid(axis="y", alpha=0.3)

    know_mean = known["s0"].mean()
    unk_mean = unknown["s0"].mean()
    ax1.axvline(know_mean, color="steelblue", linestyle="--", linewidth=1.5)
    ax1.axvline(unk_mean, color="coral", linestyle="--", linewidth=1.5)

    # --- Plot 2: Top-3 geometric mean histogram ---
    ax2 = axes[0, 1]
    known_gmean = df.loc[known_mask, "top3_gmean"]
    unknown_gmean = df.loc[unknown_mask, "top3_gmean"]
    ax2.hist(known_gmean, bins=bins, alpha=0.7, label=f"Known (n={len(known)})", color="steelblue", edgecolor="white")
    ax2.hist(unknown_gmean, bins=bins, alpha=0.7, label=f"Unknown (n={len(unknown)})", color="coral", edgecolor="white")
    ax2.set_xlabel("Top-3 Geometric Mean Score")
    ax2.set_ylabel("Count")
    ax2.set_title("Top-3 Geometric Mean: Known vs Unknown")
    ax2.legend(fontsize=8)
    ax2.set_xlim(0, 1.1)
    ax2.grid(axis="y", alpha=0.3)

    k_gmean = known_gmean.mean()
    u_gmean = unknown_gmean.mean()
    ax2.axvline(k_gmean, color="steelblue", linestyle="--", linewidth=1.5)
    ax2.axvline(u_gmean, color="coral", linestyle="--", linewidth=1.5)

    # --- Plot 3: Box plot s0_score by top 10 species ---
    ax3 = axes[1, 0]
    species_counts = df["species_label"].value_counts()
    top10 = species_counts.head(10).index.tolist()
    plot_data = []
    plot_labels = []
    for sp in top10:
        sp_data = df[df["species_label"] == sp]["s0"].dropna()
        plot_data.append(sp_data.values)
        strip = _strip_penicillium(sp)
        plot_labels.append(f"{strip[:15]}\n(n={len(sp_data)})")

    bp = ax3.boxplot(plot_data, tick_labels=plot_labels, patch_artist=True,
                     medianprops={"color": "black", "linewidth": 1.5},
                     flierprops={"markersize": 3, "alpha": 0.5})
    colors = plt.cm.tab10(np.linspace(0, 1, len(plot_data)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
    ax3.set_ylabel("s0 Score")
    ax3.set_title("s0 Score Distribution by Top 10 Species")
    ax3.set_ylim(0, 1.1)
    plt.sca(ax3)
    plt.xticks(rotation=45, fontsize=8)
    ax3.grid(axis="y", alpha=0.3)

    # --- Plot 4: s0 vs top3_gmean scatter (known only, colored by correct) ---
    ax4 = axes[1, 1]
    known_df = df[known_mask].copy()
    known_df["correct"] = known_df.apply(
        lambda r: _strip_penicillium(str(r["species_label"])) == _strip_penicillium(str(r["predicted_species"])),
        axis=1,
    )
    correct_pts = known_df[known_df["correct"]]
    wrong_pts = known_df[~known_df["correct"]]
    ax4.scatter(wrong_pts["s0"], wrong_pts["top3_gmean"], c="tomato", alpha=0.5, s=15, label=f"Wrong ({len(wrong_pts)})")
    ax4.scatter(correct_pts["s0"], correct_pts["top3_gmean"], c="forestgreen", alpha=0.7, s=20, label=f"Correct ({len(correct_pts)})")
    ax4.plot([0, 1.1], [0, 1.1], "k--", linewidth=0.5, alpha=0.3)
    ax4.set_xlabel("s0 Score")
    ax4.set_ylabel("Top-3 Geometric Mean")
    ax4.set_title("s0 vs Top-3 GMean (Known Only)")
    ax4.legend(fontsize=8)
    ax4.set_xlim(0, 1.1)
    ax4.set_ylim(0, 1.1)
    ax4.grid(alpha=0.3)

    fig.tight_layout()
    out = OUTPUT_DIR / "score_distributions.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")

    print(f"\n=== Score Stats ===")
    print(f"s0 known   mean: {know_mean:.4f}, median: {known['s0'].median():.4f}, std: {known['s0'].std():.4f}")
    print(f"s0 unknown mean: {unk_mean:.4f}, median: {unknown['s0'].median():.4f}, std: {unknown['s0'].std():.4f}")
    print(f"top3 gmean known   mean: {k_gmean:.4f}, median: {known_gmean.median():.4f}")
    print(f"top3 gmean unknown mean: {u_gmean:.4f}, median: {unknown_gmean.median():.4f}")


if __name__ == "__main__":
    main()
