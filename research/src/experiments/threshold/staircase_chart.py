"""
Staircase chart for threshold experiment.

Reads all_experiments.csv, plots every formula × algorithm pair
as one dot with a running-best staircase.

Usage:
    uv --directory research run python src/experiments/threshold/staircase_chart.py

Output: results/autoresearch/threshold.png
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import RESULTS_DIR  # noqa: E402

INPUT_CSV = RESULTS_DIR / "threshold" / "log" / "all_experiments.csv"
OUTPUT_PNG = RESULTS_DIR / "autoresearch" / "threshold.png"


def main() -> None:
    if not INPUT_CSV.exists():
        print(f"ERROR: Input CSV not found: {INPUT_CSV}")
        return

    rows: list[dict] = []
    with open(INPUT_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                f1 = float(row["f1"])
                if f1 < 0.0 or f1 > 1.0:
                    continue
                rows.append(
                    {
                        "formula": row["formula"],
                        "algorithm": row["algorithm"],
                        "f1": f1,
                    }
                )
            except (ValueError, KeyError):
                continue

    if not rows:
        print("ERROR: No valid experiment data")
        return

    n = len(rows)

    gray_x: list[int] = []
    gray_y: list[float] = []
    green_x: list[int] = []
    green_y: list[float] = []
    green_labels: list[str] = []
    running_best = 0.0

    for i, row in enumerate(rows):
        f1 = row["f1"]
        if f1 > running_best:
            green_x.append(i)
            green_y.append(f1)
            label = f"{row['formula']}_{row['algorithm']}"
            green_labels.append(label[:25])
            running_best = f1
        else:
            gray_x.append(i)
            gray_y.append(f1)

    fig, ax = plt.subplots(figsize=(12, 7))

    ax.scatter(gray_x, gray_y, color="#cccccc", s=15, zorder=2, label="discarded")
    ax.scatter(green_x, green_y, color="#2ca02c", s=60, zorder=4, label="new best")

    if green_x:
        stair_x: list[int] = [green_x[0], green_x[0]]
        stair_y: list[float] = [0.0, green_y[0]]
        for i in range(1, len(green_x)):
            stair_x.extend([green_x[i], green_x[i]])
            stair_y.extend([green_y[i - 1], green_y[i]])
        ax.plot(stair_x, stair_y, color="#2ca02c", linewidth=1.8, zorder=3)

        for x, y, lbl in zip(green_x, green_y, green_labels):
            ax.annotate(
                lbl,
                xy=(x, y),
                xytext=(6, 0),
                textcoords="offset points",
                fontsize=6,
                color="#2ca02c",
                zorder=5,
                fontweight="bold",
            )

    max_f1 = max(r["f1"] for r in rows)
    ax.set_xlabel("Experiment index", fontsize=11)
    ax.set_ylabel("F1 Score", fontsize=11)
    ax.set_title(
        f"Threshold experiment — {n} experiments (all formulas × algorithms)",
        fontsize=12,
    )
    ax.set_ylim(0, max_f1 * 1.15 if max_f1 > 0 else 1.0)
    ax.set_xlim(-1, n)
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", fontsize=9)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.2f}"))

    OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_PNG, dpi=150)
    plt.close(fig)

    best_row = max(rows, key=lambda r: r["f1"])
    print(f"Experiments plotted: {n}")
    print(f"Green dots (new bests): {len(green_x)}")
    print(f"Max F1: {best_row['f1']:.6f}")
    print(f"Best strategy: {best_row['formula']}_{best_row['algorithm']}")
    print(f"Chart saved: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
