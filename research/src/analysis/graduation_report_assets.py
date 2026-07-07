from __future__ import annotations

import json
import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent.parent.parent
EXP_DIR = ROOT / "results" / "experiment_analysis"
THRESHOLD_DIR = ROOT / "results" / "threshold"
THRESHOLD_LOG = THRESHOLD_DIR / "log"
LATEX_FIG_DIR = ROOT / "docs" / "graduation_report" / "latex" / "figures"
REPORT_FIG_DIR = ROOT / "graduation_report" / "report" / "figures"


def ensure_dirs() -> None:
    LATEX_FIG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FIG_DIR.mkdir(parents=True, exist_ok=True)


def dual_save(fig: plt.Figure, name: str) -> None:
    for out in [LATEX_FIG_DIR / name, REPORT_FIG_DIR / name]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def dual_copy(src: Path, name: str | None = None) -> None:
    target_name = name or src.name
    for out in [LATEX_FIG_DIR / target_name, REPORT_FIG_DIR / target_name]:
        shutil.copy2(src, out)


def load_analytics(folder: str) -> dict:
    with open(EXP_DIR / folder / "analytics.json") as f:
        return json.load(f)


def build_cv_comparison_chart() -> pd.DataFrame:
    rows = []
    for path in sorted(EXP_DIR.glob("*/analytics.json")):
        with open(path) as f:
            a = json.load(f)
        cfg = a["config"]
        summ = a["summary"]
        rows.append(
            {
                "folder": path.parent.name,
                "extractor": cfg["extractor"],
                "media": cfg.get("media_strategy", cfg.get("env_strategy", "")),
                "agg": cfg["agg_strategy"],
                "k": cfg["k"],
                "accuracy": summ["mean_accuracy"],
                "std": summ["std_accuracy"],
            }
        )
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.sort_values("accuracy", ascending=False)

    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [f"{r.extractor}\n{r.media}, {r.agg}, k={r.k}" for r in df.itertuples()]
    colors = ["#2ecc71" if "finetuned" in x else "#3498db" for x in df["extractor"]]
    bars = ax.bar(range(len(df)), df["accuracy"], color=colors)
    for i, (bar, acc, std) in enumerate(zip(bars, df["accuracy"], df["std"])):
        ax.text(
            i,
            bar.get_height() + 0.01,
            f"{acc:.1%}\n±{std:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Mean cross-validation accuracy")
    ax.set_title("Retrieval configuration comparison")
    ax.grid(axis="y", alpha=0.3)
    dual_save(fig, "cv_model_comparison.png")
    return df


def build_threshold_charts() -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.read_csv(THRESHOLD_DIR / "diverse_retrieval_results.csv")
    known = df[df["is_known"] == 1].copy()
    unknown = df[df["is_known"] == 0].copy()

    def norm(s: str) -> str:
        s = str(s).strip().lower()
        return s.removeprefix("penicillium ")

    known["known_correct_norm"] = known.apply(
        lambda r: norm(r["predicted_species"]) == norm(r["correct_species"]), axis=1
    )

    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(
        known["s0_score"].astype(float),
        color="#2ecc71",
        label="Known",
        kde=True,
        stat="density",
        ax=ax,
    )
    sns.histplot(
        unknown["s0_score"].astype(float),
        color="#e74c3c",
        label="Unknown",
        kde=True,
        stat="density",
        ax=ax,
    )
    ax.set_title("Threshold retrieval score distribution (s0)")
    ax.set_xlabel("Top-1 aggregated score")
    ax.legend()
    dual_save(fig, "threshold_s0_distribution.png")

    per_species = (
        known.groupby("correct_species")["known_correct_norm"]
        .agg(["mean", "count", "sum"])
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(per_species["correct_species"], per_species["mean"], color="#9b59b6")
    for bar, cnt, good in zip(bars, per_species["count"], per_species["sum"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{good}/{cnt}",
            ha="center",
            fontsize=9,
        )
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Normalized known accuracy")
    ax.set_title("Known-species threshold retrieval accuracy")
    ax.set_xticklabels(
        [x.replace("Penicillium ", "P. ") for x in per_species["correct_species"]],
        rotation=25,
        ha="right",
    )
    dual_save(fig, "threshold_known_species_accuracy.png")

    all_exp = pd.read_csv(THRESHOLD_LOG / "all_experiments.csv")
    if all_exp.empty:
        return per_species, pd.DataFrame()
    top = all_exp.sort_values("f1", ascending=False).head(10)
    fig, ax = plt.subplots(figsize=(12, 6))
    labels = [f"{f}_{a}" for f, a in zip(top["formula"], top["algorithm"])]
    bars = ax.bar(range(len(top)), top["f1"], color="#f39c12")
    for i, (bar, val) in enumerate(zip(bars, top["f1"])):
        ax.text(i, bar.get_height() + 0.01, f"{val:.3f}", ha="center", fontsize=9)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylabel("F1 score")
    ax.set_title("Top threshold strategies")
    dual_save(fig, "threshold_top_strategies.png")
    return per_species, top


def write_latex_tables(
    cv_df: pd.DataFrame, threshold_species: pd.DataFrame, threshold_top: pd.DataFrame
) -> None:
    if not cv_df.empty:
        top6 = cv_df.head(6).copy()
        lines = [
            "\\begin{table}[ht]",
            "\\centering",
            "\\caption{Best retrieval configurations from 5-fold cross-validation}",
            "\\label{tab:cv_best_configs}",
            "\\begin{tabular}{@{}llcrr@{}}",
            "\\toprule",
            r"Extractor & Aggregation & K & Mean Acc. & Std \\",
            "\\midrule",
        ]
        for r in top6.itertuples():
            extractor = str(r.extractor).replace("_", "\\_")
            agg = str(r.agg).replace("_", "\\_")
            lines.append(
                rf"{extractor} & {agg} & {r.k} & {r.accuracy:.3f} & {r.std:.3f} \\"
            )
        lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
        (
            ROOT
            / "docs"
            / "graduation_report"
            / "latex"
            / "figures"
            / "table_cv_best_configs.tex"
        ).write_text("\n".join(lines))

    if not threshold_species.empty:
        lines = [
            "\\begin{table}[ht]",
            "\\centering",
            "\\caption{Known-species threshold retrieval accuracy after label normalization}",
            "\\label{tab:threshold_known_species}",
            "\\begin{tabular}{@{}lccc@{}}",
            "\\toprule",
            r"Species & Correct & Total & Accuracy \\",
            "\\midrule",
        ]
        for r in threshold_species.itertuples():
            species = str(r.correct_species).replace("Penicillium ", "P. ")
            lines.append(
                rf"{species} & {int(r.sum)} & {int(r.count)} & {float(r.mean):.3f} \\"
            )
        lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}", ""]
        (
            ROOT
            / "docs"
            / "graduation_report"
            / "latex"
            / "figures"
            / "table_threshold_known_species.tex"
        ).write_text("\n".join(lines))

    if not threshold_top.empty:
        best = threshold_top.iloc[0]
        lines = [
            "\\begin{table}[ht]",
            "\\centering",
            "\\caption{Best threshold strategy discovered on diverse retrieval results}",
            "\\label{tab:threshold_best}",
            "\\begin{tabular}{@{}lcccc@{}}",
            "\\toprule",
            r"Formula & Algorithm & Threshold & F1 & AUROC \\",
            "\\midrule",
            rf"{str(best['formula']).replace('_', r'\_')} & {best['algorithm']} & {best['threshold']:.4f} & {best['f1']:.4f} & {best['auroc']:.4f} \\",
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            "",
        ]
        (
            ROOT
            / "docs"
            / "graduation_report"
            / "latex"
            / "figures"
            / "table_threshold_best.tex"
        ).write_text("\n".join(lines))


def main() -> None:
    ensure_dirs()
    cv_df = build_cv_comparison_chart()
    dual_copy(
        EXP_DIR / "efficientnetb1_E1_freq_strength_k7" / "confusion_matrix.png",
        "confusion_matrix_base_best.png",
    )
    dual_copy(
        EXP_DIR
        / "efficientnetb1_finetuned_E1_freq_strength_k7"
        / "confusion_matrix.png",
        "confusion_matrix_finetuned_best.png",
    )
    threshold_species, threshold_top = build_threshold_charts()
    write_latex_tables(cv_df, threshold_species, threshold_top)


if __name__ == "__main__":
    main()
