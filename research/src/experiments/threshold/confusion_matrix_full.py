"""
Build confusion matrix with UNKNOWN class from threshold retrieval results.
Saves two versions: standard and with-unknown-highlighted.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from sklearn.metrics import confusion_matrix  # noqa: E402

from src.config import CURATED_METADATA_PATH, RESULTS_DIR  # noqa: E402


CSV_PATH = RESULTS_DIR / "threshold" / "diverse_retrieval_results.csv"
OUTPUT_DIR = RESULTS_DIR / "threshold"


def _load_known_species() -> Set[str]:
    species: Set[str] = set()
    if not CURATED_METADATA_PATH.exists():
        return species
    with open(CURATED_METADATA_PATH) as f:
        curated = json.load(f)
    for item in curated:
        info = item.get("instance_info", item.get("data", {}))
        sp = info.get("species", "")
        if sp and sp.lower() != "unknown":
            species.add(sp.strip().lower())
            species.add(_strip_penicillium(sp).lower())
    return species


def _strip_penicillium(label: str) -> str:
    clean = str(label).strip().lower()
    for prefix in ("penicillium ",):
        if clean.startswith(prefix):
            return clean[len(prefix) :]
    return clean


def _shorten_label(label: str) -> str:
    s = _strip_penicillium(label)
    if len(s) > 22:
        parts = s.split()
        if len(parts) > 1:
            return parts[-1][:8] + "."
        return s[:20] + "."
    return s


def _build_labels(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    y_true: List[str] = []
    y_pred: List[str] = []

    for _, row in df.iterrows():
        is_known = int(row["is_known"])
        species_label = str(row["species_label"])
        predicted = str(row["predicted_species"])

        if is_known == 1:
            y_true.append(_strip_penicillium(species_label))
        else:
            y_true.append("UNKNOWN")

        y_pred.append(_strip_penicillium(predicted))

    return y_true, y_pred


def _filter_labels(labels: List[str]) -> List[str]:
    all_labels = set(labels)
    filtered = sorted(label for label in all_labels if label != "UNKNOWN")
    if "UNKNOWN" in all_labels:
        filtered.append("UNKNOWN")
    return filtered


def draw_standard(
    cm_df: pd.DataFrame, accuracy: float, known_count: int, total: int
) -> None:
    labels = list(cm_df.columns)
    n = len(labels)
    figsize = max(14, n * 0.45), max(11, n * 0.38)

    fig, ax = plt.subplots(figsize=figsize)
    sns.heatmap(
        cm_df,
        annot=True,
        fmt="d",
        xticklabels=labels,
        yticklabels=labels,
        cmap="YlOrRd",
        ax=ax,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"fontsize": 6},
        cbar_kws={"shrink": 0.8},
    )
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("True", fontsize=11)
    ax.set_title(
        f"Confusion Matrix (with UNKNOWN)\n"
        f"Accuracy (known only): {accuracy:.3f} | Known: {known_count} | Total: {total}",
        fontsize=12,
        fontweight="bold",
    )
    plt.xticks(rotation=90, fontsize=6)
    plt.yticks(rotation=0, fontsize=6)
    fig.tight_layout()

    out = OUTPUT_DIR / "confusion_matrix_full.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def draw_with_unknown_highlighted(
    cm_df: pd.DataFrame, accuracy: float, known_count: int, total: int
) -> None:
    labels = list(cm_df.columns)
    n = len(labels)

    annot_matrix = cm_df.copy().astype(str)

    figsize = max(16, n * 0.5), max(13, n * 0.42)

    fig, ax = plt.subplots(figsize=figsize)

    sns.heatmap(
        cm_df,
        annot=annot_matrix,
        fmt="",
        xticklabels=labels,
        yticklabels=labels,
        cmap="YlOrRd",
        ax=ax,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"fontsize": 6},
        cbar_kws={"shrink": 0.8},
    )

    if "UNKNOWN" in labels:
        uidx = labels.index("UNKNOWN")
        for j in range(n):
            rect = plt.Rectangle(
                (j, uidx), 1, 1, fill=False, edgecolor="red", linewidth=2.5
            )
            ax.add_patch(rect)
        for i in range(n):
            rect = plt.Rectangle(
                (uidx, i), 1, 1, fill=False, edgecolor="red", linewidth=2.5
            )
            ax.add_patch(rect)

    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("True", fontsize=11)
    ax.set_title(
        f"Confusion Matrix — UNKNOWN Boundaries Highlighted\n"
        f"Accuracy (known only): {accuracy:.3f} | Known: {known_count} | Total: {total}",
        fontsize=12,
        fontweight="bold",
    )
    plt.xticks(rotation=90, fontsize=6)
    plt.yticks(rotation=0, fontsize=6)
    fig.tight_layout()

    out = OUTPUT_DIR / "confusion_matrix_with_unknown.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def _build_simplified_labels(df: pd.DataFrame) -> Tuple[List[str], List[str]]:
    """Build simplified labels: only known species + UNKNOWN for true labels.
    Predicted labels: known species get their prediction, unknowns get their
    prediction OR 'UNKNOWN' if confidence < threshold. Then group rare preds."""
    y_true: List[str] = []
    y_pred: List[str] = []

    for _, row in df.iterrows():
        is_known = int(row["is_known"])
        species_label = str(row["species_label"])
        predicted = _strip_penicillium(str(row["predicted_species"]))

        if is_known == 1:
            y_true.append(_strip_penicillium(species_label))
            y_pred.append(predicted)
        else:
            y_true.append("UNKNOWN")
            y_pred.append(predicted)

    return y_true, y_pred


def draw_simplified(
    y_true: List[str], y_pred: List[str], accuracy: float, known_count: int, total: int
) -> None:
    """Confusion matrix where only known species are shown + aggregated 'other'."""
    from collections import Counter

    known_true = set(t for t in y_true if t != "UNKNOWN")

    # find top predicted classes for the UNKNOWN row
    unk_pred_counts = Counter(yp for yt, yp in zip(y_true, y_pred) if yt == "UNKNOWN")
    top_unk_preds = set(sp for sp, _ in unk_pred_counts.most_common(5))

    # combine known species + top unknown predictions
    top_labels = sorted(known_true | top_unk_preds)

    y_true_simple = []
    y_pred_simple = []
    for yt, yp in zip(y_true, y_pred):
        if yt not in top_labels and yt != "UNKNOWN":
            yt_clean = "other_known"
        else:
            yt_clean = yt
        if yp not in top_labels:
            yp_clean = "other_pred"
        else:
            yp_clean = yp
        y_true_simple.append(yt_clean)
        y_pred_simple.append(yp_clean)

    all_simple = sorted(set(y_true_simple + y_pred_simple))
    if "UNKNOWN" in all_simple:
        all_simple.remove("UNKNOWN")
        all_simple.append("UNKNOWN")

    cm = confusion_matrix(y_true_simple, y_pred_simple, labels=all_simple)
    cm_df_simple = pd.DataFrame(cm, index=all_simple, columns=all_simple)

    n = len(all_simple)
    figsize = max(14, n * 0.7), max(10, n * 0.55)
    fig, ax = plt.subplots(figsize=figsize)
    annot_s = cm_df_simple.copy().astype(str)

    sns.heatmap(
        cm_df_simple,
        annot=annot_s,
        fmt="",
        xticklabels=all_simple,
        yticklabels=all_simple,
        cmap="YlOrRd",
        ax=ax,
        linewidths=1,
        linecolor="white",
        annot_kws={"fontsize": 9},
        cbar_kws={"shrink": 0.8},
    )

    if "UNKNOWN" in all_simple:
        uidx = all_simple.index("UNKNOWN")
        for j in range(n):
            rect = plt.Rectangle(
                (j, uidx), 1, 1, fill=False, edgecolor="red", linewidth=3
            )
            ax.add_patch(rect)

    ax.set_xlabel("Predicted", fontsize=12)
    ax.set_ylabel("True", fontsize=12)
    ax.set_title(
        f"Simplified Confusion Matrix — UNKNOWN Class Highlighted\n"
        f"Accuracy (known only): {accuracy:.3f} | Known: {known_count} | Total: {total}",
        fontsize=13,
        fontweight="bold",
    )
    plt.xticks(rotation=45, fontsize=10, ha="right")
    plt.yticks(rotation=0, fontsize=10)
    fig.tight_layout()

    out = OUTPUT_DIR / "confusion_matrix_simplified.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def print_summary(y_true: List[str], y_pred: List[str], df: pd.DataFrame) -> None:
    unknown_true = sum(1 for y in y_true if y == "UNKNOWN")
    total_known = sum(1 for y in y_true if y != "UNKNOWN")

    unknown_as_known_count = 0
    known_as_unknown_count = 0
    for yt, yp in zip(y_true, y_pred):
        if yt == "UNKNOWN" and yp != "UNKNOWN":
            unknown_as_known_count += 1
        elif yt != "UNKNOWN" and yp == "UNKNOWN":
            known_as_unknown_count += 1

    correct_known = sum(
        1 for yt, yp in zip(y_true, y_pred) if yt == yp and yt != "UNKNOWN"
    )

    # Check: are unknown predictions actually known DB species?
    known_species = _load_known_species()
    unknown_pred_as_known_db = 0
    unknown_pred_dest: Dict[str, int] = {}
    for yt, yp in zip(y_true, y_pred):
        if yt == "UNKNOWN":
            unknown_pred_dest[yp] = unknown_pred_dest.get(yp, 0) + 1
            if yp in known_species:
                unknown_pred_as_known_db += 1

    acc = correct_known / max(total_known, 1)

    print("\n=== Confusion Matrix Summary ===")
    print(f"Total samples:               {len(y_true)}")
    print(f"Known samples:               {total_known}")
    print(f"Unknown samples:             {unknown_true}")
    print(f"Unknown predicted as a known DB species: {unknown_pred_as_known_db}")
    print(f"Known correct:               {correct_known}")
    print(f"Known accuracy:              {acc:.4f}")

    print("\nPer-species accuracy (known only):")
    known_df = df[df["is_known"] == 1].copy()
    sp_correct: Dict[str, int] = {}
    sp_total: Dict[str, int] = {}
    for _, row in known_df.iterrows():
        sp = _strip_penicillium(str(row["species_label"]))
        pred = _strip_penicillium(str(row["predicted_species"]))
        sp_total[sp] = sp_total.get(sp, 0) + 1
        if sp == pred:
            sp_correct[sp] = sp_correct.get(sp, 0) + 1
    for sp in sorted(sp_total.keys(), key=lambda s: sp_total[s], reverse=True):
        c = sp_correct.get(sp, 0)
        t = sp_total[sp]
        print(f"  {sp:25s}: {c:3d}/{t:3d} = {c / t:.3f}")

    print("\nUnknown predictions — top destinations:")
    for sp, cnt in sorted(unknown_pred_dest.items(), key=lambda x: -x[1])[:15]:
        marker = " [KNOWN DB]" if sp in known_species else ""
        print(f"  -> {sp:30s}: {cnt:4d}{marker}")


def main() -> None:
    known_species = _load_known_species()
    print(f"Loaded {len(known_species)} known species variants from curated DB")

    df = pd.read_csv(CSV_PATH)

    y_true, y_pred = _build_simplified_labels(df)

    all_labels = _filter_labels(y_true + y_pred)
    print(f"Unique classes: {len(all_labels)}")

    cm = confusion_matrix(y_true, y_pred, labels=all_labels)
    cm_df = pd.DataFrame(cm, index=all_labels, columns=all_labels)

    correct_known = sum(
        1 for yt, yp in zip(y_true, y_pred) if yt == yp and yt != "UNKNOWN"
    )
    total_known = sum(1 for y in y_true if y != "UNKNOWN")
    accuracy = correct_known / max(total_known, 1)

    draw_standard(cm_df, accuracy, total_known, len(y_true))
    draw_with_unknown_highlighted(cm_df, accuracy, total_known, len(y_true))
    draw_simplified(y_true, y_pred, accuracy, total_known, len(y_true))
    print_summary(y_true, y_pred, df)


if __name__ == "__main__":
    main()
