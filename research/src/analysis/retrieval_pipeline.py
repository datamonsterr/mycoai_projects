from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from qdrant_client import QdrantClient

from src.config import QDRANT_API_KEY, QDRANT_URL, RESULTS_DIR
from src.experiments.retrieval.run import get_extractor_by_name, run_species_evaluation

PIPELINE_DIR = RESULTS_DIR / "retrieval_pipeline"
RETRIEVAL_SWEEP_DIR = PIPELINE_DIR / "retrieval_sweep"
ANALYTICS_DIR = PIPELINE_DIR / "analytics"
GRAD_REPORT_FIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "graduation_report" / "report" / "figures"
LATEX_FIG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "graduation_report" / "latex" / "figures"


@dataclass(frozen=True)
class RetrievalConfig:
    extractor: str
    media: str
    aggregation: str
    k: int = 7

    @property
    def folder_name(self) -> str:
        return f"{self.extractor}_{self.aggregation}_{self.media}"


def media_to_environment(media: str) -> str | None:
    if media == "E1":
        return None
    if media in {"all", "E2"}:
        return "all"
    return media


def default_extractors() -> list[str]:
    return [
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
    ]


def default_media() -> list[str]:
    return [
        "E1",
        "all",
        "E3_CREA",
        "E3_CYA",
        "E3_CYA30",
        "E3_CYAS",
        "E3_DG18",
        "E3_MEA",
        "E3_YES",
        "E4_CREA",
        "E4_CYA",
        "E4_CYA30",
        "E4_CYAS",
        "E4_DG18",
        "E4_MEA",
        "E4_YES",
    ]


def default_aggregations() -> list[str]:
    return ["weighted", "uni", "freq_strength", "relative"]


def run_retrieval_sweep(
    collection: str,
    extractors: list[str] | None = None,
    media_values: list[str] | None = None,
    aggregations: list[str] | None = None,
    k: int = 7,
) -> Path:
    RETRIEVAL_SWEEP_DIR.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=120)
    summary_rows: list[dict[str, Any]] = []
    configs = [
        RetrievalConfig(extractor, media, agg, k)
        for extractor in (extractors or default_extractors())
        for media in (media_values or default_media())
        for agg in (aggregations or default_aggregations())
    ]
    for config in configs:
        out_dir = RETRIEVAL_SWEEP_DIR / config.folder_name
        out_dir.mkdir(parents=True, exist_ok=True)
        extractor = get_extractor_by_name(config.extractor)
        if extractor is None:
            raise ValueError(f"Unknown extractor: {config.extractor}")
        results, _ = run_species_evaluation(
            client=client,
            collection_name=collection,
            feature_extractor=extractor,
            k=config.k,
            without_siblings=True,
            environment=media_to_environment(config.media),
            strategy=config.aggregation,
            output_dir=str(out_dir),
            generate_visualizations=False,
        )
        correct = sum(1 for row in results if row.get("correct"))
        total = len(results)
        summary_rows.append(
            {
                **asdict(config),
                "accuracy": correct / total if total else 0.0,
                "correct": correct,
                "total": total,
                "collection": collection,
                "result_dir": str(out_dir),
            }
        )
    summary_path = RETRIEVAL_SWEEP_DIR / "accuracy_summary.csv"
    pd.DataFrame(summary_rows).sort_values("accuracy", ascending=False).to_csv(summary_path, index=False)
    (RETRIEVAL_SWEEP_DIR / "manifest.json").write_text(
        json.dumps({"collection": collection, "k": k, "runs": summary_rows}, indent=2)
    )
    return summary_path


def build_retrieval_charts(summary_csv: Path) -> list[Path]:
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(summary_csv)
    outputs: list[Path] = []
    if df.empty:
        return outputs
    top = df.head(20).copy()
    fig, ax = plt.subplots(figsize=(14, 7))
    top_cols = top.columns.tolist()
    agg_col = next((c for c in top_cols if c in ('aggregation', 'agg')), top_cols[1])
    media_col = next((c for c in top_cols if c in ('media', 'media_strategy')), top_cols[2])
    extractor_col = next((c for c in top_cols if c in ('extractor', 'feature_extractor')), top_cols[0])
    labels = [f"{r.__getattribute__(extractor_col)}\n{r.__getattribute__(media_col)} {r.__getattribute__(agg_col)}" for r in top.itertuples()]
    bars = ax.bar(range(len(top)), top["accuracy"], color="#2E8B57")
    for bar, value in zip(bars, top["accuracy"]):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.01, f"{value:.2f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylim(0, min(1.15, max(1.0, float(top["accuracy"].max()) + 0.15)))
    ax.set_ylabel("Accuracy")
    ax.set_title("Top retrieval sweep configurations (K=7)")
    ax.grid(axis="y", alpha=0.3)
    path = ANALYTICS_DIR / "retrieval_top_configs.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path)

    pivot_cols = df.columns.tolist()
    extractor_col = next((c for c in pivot_cols if c in ('extractor', 'feature_extractor')), pivot_cols[0])
    media_col = next((c for c in pivot_cols if c in ('media', 'media_strategy')), pivot_cols[2])
    pivot = df.pivot_table(index=extractor_col, columns=media_col, values="accuracy", aggfunc="max")
    fig, ax = plt.subplots(figsize=(14, 7))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="viridis", ax=ax)
    ax.set_title("Best retrieval accuracy by extractor and media selection")
    path = ANALYTICS_DIR / "retrieval_media_heatmap.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    outputs.append(path)
    return outputs


def publish_figures(paths: list[Path]) -> None:
    for target_dir in [GRAD_REPORT_FIG_DIR, LATEX_FIG_DIR]:
        target_dir.mkdir(parents=True, exist_ok=True)
        for path in paths:
            shutil.copy2(path, target_dir / path.name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval pipeline sweep and analytics")
    parser.add_argument("--collection", default="qdrant-research")
    parser.add_argument("--skip-sweep", action="store_true")
    args = parser.parse_args()
    summary = RETRIEVAL_SWEEP_DIR / "accuracy_summary.csv"
    if not args.skip_sweep:
        summary = run_retrieval_sweep(collection=args.collection)
    charts = build_retrieval_charts(summary)
    publish_figures(charts)
    print(json.dumps({"summary": str(summary), "charts": [str(p) for p in charts]}, indent=2))


if __name__ == "__main__":
    main()
