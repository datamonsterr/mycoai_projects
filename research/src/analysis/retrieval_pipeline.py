from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from qdrant_client import QdrantClient

from src.config import QDRANT_API_KEY, QDRANT_URL, RESULTS_DIR
from src.experiments.retrieval.run import get_extractor_by_name, run_species_evaluation

PIPELINE_DIR = RESULTS_DIR / "retrieval_pipeline"
RETRIEVAL_SWEEP_DIR = PIPELINE_DIR / "retrieval_sweep"
ANALYTICS_DIR = PIPELINE_DIR / "analytics"
GRAD_REPORT_FIG_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "graduation_report"
    / "figures"
    / "06_retrieval"
)
LATEX_FIG_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "graduation_report"
    / "figures"
    / "06_retrieval"
)


def run_retrieval_sweep(
    collection: str,
    extractors: list[str],
    media_values: list[str],
    aggregations: list[str],
    ks: list[int],
) -> Path:
    RETRIEVAL_SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)
    rows: list[dict] = []

    for extractor_name in extractors:
        extractor = get_extractor_by_name(extractor_name)
        if extractor is None:
            continue
        for media in media_values:
            for agg in aggregations:
                for k in ks:
                    out_dir = (
                        RETRIEVAL_SWEEP_DIR / f"{extractor_name}_{media}_{agg}_k{k}"
                    )
                    out_dir.mkdir(parents=True, exist_ok=True)
                    environment = (
                        None if media == "E1" else ("all" if media == "E2" else media)
                    )
                    results, _ = run_species_evaluation(
                        client=client,
                        collection_name=collection,
                        feature_extractor=extractor,
                        k=k,
                        without_siblings=True,
                        environment=environment,
                        strategy=agg,
                        output_dir=str(out_dir),
                        generate_visualizations=False,
                    )
                    correct = sum(1 for row in results if row.get("correct"))
                    total = len(results)
                    rows.append(
                        {
                            "extractor": extractor_name,
                            "media": media,
                            "aggregation": agg,
                            "k": k,
                            "accuracy": correct / total if total else 0.0,
                            "correct": correct,
                            "total": total,
                            "result_dir": str(out_dir),
                        }
                    )
    summary = pd.DataFrame(rows).sort_values(
        ["accuracy", "extractor", "media", "aggregation", "k"],
        ascending=[False, True, True, True, True],
    )
    summary_path = RETRIEVAL_SWEEP_DIR / "accuracy_summary.csv"
    summary.to_csv(summary_path, index=False)
    return summary_path


def _save(fig: plt.Figure, name: str, outputs: list[Path]) -> None:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    out = ANALYTICS_DIR / name
    fig.savefig(out, dpi=250, bbox_inches="tight")
    plt.close(fig)
    outputs.append(out)


def build_retrieval_charts(summary_csv: Path) -> list[Path]:
    df = pd.read_csv(summary_csv)
    outputs: list[Path] = []
    if df.empty:
        return outputs

    family_map = {
        "hog": "traditional",
        "gabor": "traditional",
        "colorhistogram": "traditional",
        "colorhistogramhs": "traditional",
        "resnet50": "pretrained",
        "mobilenetv2": "pretrained",
        "efficientnetb1": "pretrained",
        "resnet50_finetuned": "fine-tuned",
        "mobilenetv2_finetuned": "fine-tuned",
        "efficientnetb1_finetuned": "fine-tuned",
    }
    df["family"] = df["extractor"].map(family_map).fillna("other")

    top15 = df.head(15).copy()
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [
        f"{r.extractor}\n{r.media}-{r.aggregation}-k{r.k}" for r in top15.itertuples()
    ]
    palette = {
        "fine-tuned": "#2E8B57",
        "pretrained": "#4A90D9",
        "traditional": "#C97A2B",
        "other": "#777777",
    }
    bars = ax.bar(
        range(len(top15)),
        top15["accuracy"],
        color=[palette[f] for f in top15["family"]],
    )
    for i, bar in enumerate(bars):
        ax.text(
            i,
            bar.get_height() + 0.01,
            f"{top15.iloc[i]['accuracy']:.2f}",
            ha="center",
            fontsize=8,
        )
    ax.set_xticks(range(len(top15)))
    ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Accuracy")
    ax.set_title("Top 15 retrieval configurations")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "retrieval_top15_accuracy.png", outputs)

    extractor_rows: list[dict[str, float | str]] = []
    extractor_sources = [
        RESULTS_DIR / "retrieval_batch1",
        RESULTS_DIR / "retrieval_batch2",
        RESULTS_DIR / "retrieval_batch3",
    ]
    extractor_setting = "5_freq_strength_E1_yolo"
    for source_dir in extractor_sources:
        for csv_path in sorted(source_dir.glob(f"*_{extractor_setting}/*.csv")):
            run_df = pd.read_csv(csv_path)
            if run_df.empty:
                continue
            extractor_name = str(run_df["feature_extractor"].iloc[0])
            extractor_rows.append(
                {
                    "extractor": extractor_name,
                    "accuracy": float(
                        (run_df["predicted_species"] == run_df["ground_truth"]).mean()
                    ),
                    "family": family_map.get(extractor_name, "other"),
                }
            )

    extractor_stats = pd.DataFrame(extractor_rows)
    if not extractor_stats.empty:
        family_order = {"fine-tuned": 0, "pretrained": 1, "traditional": 2, "other": 3}
        extractor_stats["family_order"] = (
            extractor_stats["family"].map(family_order).fillna(9)
        )
        extractor_stats = extractor_stats.sort_values(
            ["family_order", "accuracy"], ascending=[True, False]
        )
        fig, ax = plt.subplots(figsize=(11.5, 5.8))
        x = range(len(extractor_stats))
        bars = ax.bar(
            x,
            extractor_stats["accuracy"],
            color=[palette[f] for f in extractor_stats["family"]],
        )
        for i, bar in enumerate(bars):
            ax.text(
                i,
                bar.get_height() + 0.01,
                f"{extractor_stats.iloc[i]['accuracy']:.2f}",
                ha="center",
                fontsize=8,
            )
        ax.set_xticks(list(x))
        ax.set_xticklabels(
            extractor_stats["extractor"].tolist(), rotation=35, ha="right"
        )
        ax.set_ylabel("Accuracy")
        ax.set_ylim(0, 1.0)
        ax.set_title("Extractor comparison: YOLO, E1, freq_strength, K=5")
        ax.grid(axis="y", alpha=0.3)
        _save(fig, "retrieval_extractor_family.png", outputs)

    media_rows: list[dict[str, float | int | str]] = []
    for csv_path in sorted(
        RESULTS_DIR.glob("retrieval_*/efficientnetb1_finetuned_*_E*_yolo/*.csv")
    ):
        run_df = pd.read_csv(csv_path)
        if run_df.empty or "predicted_species" not in run_df.columns:
            continue
        match = re.match(
            r"^(?P<extractor>.+?)_(?P<k>\d+)_(?P<aggregation>weighted|uni|relative|per_species_avg|max_score|perquery_avg|perquery_norm_avg|freq_strength)_(?P<media>E1|E2|E3_[A-Z0-9]+|E4_[A-Z0-9]+)_yolo$",
            csv_path.stem,
        )
        if not match:
            continue
        extractor_name = match.group("extractor")
        if extractor_name != "efficientnetb1_finetuned":
            continue
        k = int(match.group("k"))
        aggregation = match.group("aggregation")
        media = match.group("media")
        media_rows.append(
            {
                "media": media,
                "aggregation": aggregation,
                "k": k,
                "accuracy": float(
                    (run_df["predicted_species"] == run_df["ground_truth"]).mean()
                ),
            }
        )

    media_best = pd.DataFrame(media_rows)
    if not media_best.empty:
        media_best = media_best.sort_values(
            ["media", "accuracy"], ascending=[True, False]
        )
        media_best = media_best.groupby("media", as_index=False).first()

        def media_group(media: str) -> str:
            if media == "E1":
                return "E1"
            if media == "E2":
                return "E2"
            if media.startswith("E3_"):
                return "E3"
            if media.startswith("E4_"):
                return "E4"
            return "other"

        media_best["media_group"] = media_best["media"].map(media_group)
        group_colors = {
            "E1": "#2E8B57",
            "E2": "#4A90D9",
            "E3": "#C97A2B",
            "E4": "#A855F7",
            "other": "#777777",
        }
        media_best = media_best.sort_values("accuracy", ascending=True)
        fig, ax = plt.subplots(figsize=(10.5, 7.2))
        bars = ax.barh(
            media_best["media"],
            media_best["accuracy"],
            color=[group_colors[g] for g in media_best["media_group"]],
        )
        for bar, (_, row) in zip(bars, media_best.iterrows()):
            ax.text(
                row["accuracy"] + 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{row['accuracy']:.2f} | {row['aggregation']} | K={int(row['k'])}",
                va="center",
                fontsize=7,
            )
        legend_handles = [
            plt.matplotlib.patches.Patch(facecolor=group_colors[key], label=key)
            for key in ["E1", "E2", "E3", "E4"]
        ]
        ax.legend(handles=legend_handles, title="Media family", fontsize=8)
        ax.set_xlabel("Best retrieval accuracy")
        ax.set_ylabel("Media strategy")
        ax.set_xlim(0, 1.0)
        ax.set_title("EfficientNetB1 fine-tuned: best raw result per media strategy")
        ax.grid(axis="x", alpha=0.3)
        _save(fig, "retrieval_heatmap_k_vs_media.png", outputs)

    best_family = df[df["extractor"] == "efficientnetb1_finetuned"]
    heatmap_agg_k = best_family.pivot_table(
        index="aggregation", columns="k", values="accuracy", aggfunc="max"
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        heatmap_agg_k,
        annot=True,
        fmt=".2f",
        cmap="magma",
        ax=ax,
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("EfficientNetB1 fine-tuned: aggregation vs K")
    _save(fig, "retrieval_heatmap_k_vs_agg.png", outputs)

    grouped = (
        best_family.groupby(["media", "k"])
        .agg(accuracy=("accuracy", "max"))
        .reset_index()
    )
    heatmap_media_k = grouped.pivot(index="media", columns="k", values="accuracy")
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(
        heatmap_media_k,
        annot=True,
        fmt=".2f",
        cmap="viridis",
        ax=ax,
        cbar_kws={"shrink": 0.8},
    )
    ax.set_title("EfficientNetB1 fine-tuned: media strategy vs K")
    _save(fig, "retrieval_heatmap_agg_vs_media.png", outputs)

    readability_rows: list[dict[str, float | str]] = []
    retrieval_k7_dir = RESULTS_DIR / "retrieval_k7"
    for csv_path in sorted(
        retrieval_k7_dir.glob("efficientnetb1_finetuned_7_*_E1_yolo/*.csv")
    ):
        run_df = pd.read_csv(csv_path)
        if run_df.empty:
            continue
        scores = run_df["predicted_confidence"].astype(float)
        readability_rows.append(
            {
                "aggregation": str(run_df["aggregation"].iloc[0]),
                "mean_top1_score": float(scores.mean()),
                "std_top1_score": float(scores.std()),
                "min_top1_score": float(scores.min()),
                "max_top1_score": float(scores.max()),
            }
        )

    readability_df = pd.DataFrame(readability_rows)
    if not readability_df.empty:
        strategy_order = [
            "weighted",
            "uni",
            "relative",
            "per_species_avg",
            "max_score",
            "perquery_avg",
            "perquery_norm_avg",
            "freq_strength",
        ]
        label_map = {
            "weighted": "weighted",
            "uni": "uni",
            "relative": "relative",
            "per_species_avg": "per_species_avg",
            "max_score": "max_score",
            "perquery_avg": "perquery_avg",
            "perquery_norm_avg": "perquery_norm_avg",
            "freq_strength": "freq_strength",
        }
        readability_df["aggregation"] = pd.Categorical(
            readability_df["aggregation"], categories=strategy_order, ordered=True
        )
        readability_df = readability_df.sort_values("aggregation")

        x_labels = [label_map[str(v)] for v in readability_df["aggregation"]]
        x_pos = np.arange(len(x_labels))

        fig, ax = plt.subplots(figsize=(11.5, 5.2))
        bars = ax.bar(
            x_pos,
            readability_df["mean_top1_score"],
            color="#5B84B1",
            width=0.62,
            label="Mean $s_0$",
        )
        ax.errorbar(
            x_pos,
            readability_df["mean_top1_score"],
            yerr=readability_df["std_top1_score"],
            fmt="none",
            ecolor="#2F3E46",
            capsize=4,
            linewidth=1.2,
            label=r"Mean $\pm$ std",
        )
        ax.vlines(
            x_pos,
            readability_df["min_top1_score"],
            readability_df["max_top1_score"],
            colors="#E07A5F",
            linewidth=2.0,
            alpha=0.95,
            label="Min--max range",
        )
        ax.scatter(
            x_pos,
            readability_df["min_top1_score"],
            color="#E07A5F",
            s=18,
            zorder=3,
        )
        ax.scatter(
            x_pos,
            readability_df["max_top1_score"],
            color="#E07A5F",
            s=18,
            zorder=3,
        )
        for bar, val in zip(bars, readability_df["mean_top1_score"]):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                val + 0.015,
                f"{val:.2f}",
                ha="center",
                fontsize=8,
            )
        ax.set_ylabel("Top-ranked score ($s_0$)")
        ax.set_xticks(x_pos, x_labels)
        ax.set_ylim(0, 1.0)
        ax.set_title(
            "Aggregation score readability: EfficientNetB1 fine-tuned, YOLO, E1, K=7"
        )
        ax.grid(axis="y", alpha=0.3)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
        _save(fig, "aggregation_score_readability.png", outputs)

    return outputs


def publish_figures(paths: list[Path]) -> None:
    for target_dir in [GRAD_REPORT_FIG_DIR, LATEX_FIG_DIR]:
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            shutil.copy2(path, target_dir / path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run retrieval pipeline sweep and analytics"
    )
    parser.add_argument("--collection", default="qdrant-research")
    parser.add_argument("--skip-sweep", action="store_true")
    args = parser.parse_args()
    summary = RETRIEVAL_SWEEP_DIR / "accuracy_summary.csv"
    if not args.skip_sweep:
        summary = run_retrieval_sweep(
            collection=args.collection,
            extractors=[
                "efficientnetb1_finetuned",
                "resnet50_finetuned",
                "mobilenetv2_finetuned",
                "efficientnetb1",
                "resnet50",
                "mobilenetv2",
                "hog",
                "gabor",
                "colorhistogram",
                "colorhistogramhs",
            ],
            media_values=[
                "E1",
                "E2",
                "E3_CREA",
                "E3_CYA",
                "E3_DG18",
                "E3_MEA",
                "E3_YES",
            ],
            aggregations=["weighted", "uni", "relative", "freq_strength"],
            ks=[3, 5, 7, 11, 13, 15],
        )
    charts = build_retrieval_charts(summary)
    publish_figures(charts)
    print(
        json.dumps(
            {"summary": str(summary), "charts": [str(p) for p in charts]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
