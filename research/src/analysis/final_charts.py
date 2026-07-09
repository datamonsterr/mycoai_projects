"""Generate all graduation report charts from experiment results."""

from pathlib import Path
import json
import shutil
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

GRAD = Path("/home/dat/dev/mycoai/graduation_report/report/figures")
LATEX = Path("/home/dat/dev/mycoai/graduation_report/figures")
for d in [GRAD, LATEX]:
    d.mkdir(parents=True, exist_ok=True)


def save(name, fig):
    for out in [GRAD / name, LATEX / name]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def copy_img(src_name, dst_name):
    src = Path(src_name)
    if src.exists():
        for out in [GRAD / dst_name, LATEX / dst_name]:
            shutil.copy2(src, out)


# ── 1. Segmentation comparison ──────────────────────────────────────────────
yolo_csv = Path(
    "/home/dat/dev/mycoai/results/retrieval_batch1/efficientnetb1_finetuned_5_freq_strength_E1_yolo/efficientnetb1_finetuned_5_freq_strength_E1_yolo.csv"
)
kmeans_csv = Path(
    "/home/dat/dev/mycoai/results/retrieval_report_charts_kmeans_k5_real/efficientnetb1_finetuned_5_freq_strength_E1_kmeans/efficientnetb1_finetuned_5_freq_strength_E1_kmeans.csv"
)

yolo_df = pd.read_csv(yolo_csv)
kmeans_df = pd.read_csv(kmeans_csv)
yolo_acc = float((yolo_df["predicted_species"] == yolo_df["ground_truth"]).mean())
kmeans_acc = float((kmeans_df["predicted_species"] == kmeans_df["ground_truth"]).mean())

fig, ax = plt.subplots(figsize=(8, 2.6))
labels = ["YOLO", "KMeans"]
values = [yolo_acc, kmeans_acc]
colors = ["#2ecc71", "#3498db"]
y_pos = [0.65, 0.15]
bars = ax.barh(y_pos, values, height=0.18, color=colors)
for bar, value in zip(bars, values):
    ax.text(
        value + 0.01,
        bar.get_y() + bar.get_height() / 2,
        f"{value:.3f}",
        va="center",
        fontsize=10,
        fontweight="bold",
    )
ax.set_yticks(y_pos)
ax.set_yticklabels(labels)
ax.set_xlim(0, 1.0)
ax.set_xlabel("Strain-level retrieval accuracy")
ax.set_title("Segmentation comparison under matched retrieval settings")
ax.grid(axis="x", alpha=0.3)
save("retrieval_yolo_vs_kmeans.png", fig)
print("1/5 segmentation comparison done")

# ── 2. Training curves ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
for fi in range(5):
    hp = Path(
        f"/home/dat/dev/mycoai_projects/weights/fold{fi}_EfficientNetB1_history.json"
    )
    if hp.exists():
        h = json.loads(hp.read_text())
        ax.plot(h.get("val_acc", []), label=f"Fold {fi + 1}", linewidth=2)
ax.set_xlabel("Epoch")
ax.set_ylabel("Validation Accuracy")
ax.set_title("Fold-specific EfficientNetB1 Training")
ax.legend()
ax.grid(alpha=0.3)
save("training_curves_folds.png", fig)
print("2/5 training curves done")

# ── 3. CV best configs bar ───────────────────────────────────────────────────
cv_sum = pd.read_csv(
    "/home/dat/dev/mycoai_projects/results/cross_validation/cv_summary_table.csv"
)
top6 = cv_sum.head(6)
fig, ax = plt.subplots(figsize=(12, 6))
labels = [f"{r.media_strategy} {r.agg_strategy} k{r.k}" for r in top6.itertuples()]
bars = ax.bar(range(len(top6)), top6["mean_accuracy"], color="#2ecc71")
for i, (bar, acc, std) in enumerate(
    zip(bars, top6["mean_accuracy"], top6["std_accuracy"])
):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        acc + 0.01,
        f"{acc:.3f}",
        ha="center",
        fontsize=9,
    )
ax.set_xticks(range(len(top6)))
ax.set_xticklabels(labels, rotation=30, ha="right")
ax.set_ylim(0, 1.0)
ax.set_ylabel("Mean Accuracy")
ax.set_title("Best CV Configurations (EfficientNetB1 Finetuned, 5-fold)")
ax.grid(axis="y", alpha=0.3)
save("cv_fold_configs.png", fig)
print("3/5 cv configs done")

# ── 4. Per-fold accuracy ────────────────────────────────────────────────────
cv_df = pd.read_csv(
    "/home/dat/dev/mycoai_projects/results/cross_validation/cv_results.csv"
)
fold_means = cv_df.groupby("fold")["correct"].mean()
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(
    fold_means.index,
    fold_means.values,
    color=["#3498db", "#2ecc71", "#f39c12", "#e74c3c", "#9b59b6"],
)
for f, acc in fold_means.items():
    ax.text(f, acc + 0.01, f"{acc:.3f}", ha="center")
ax.set_xlabel("Fold")
ax.set_ylabel("Accuracy")
ax.set_ylim(0, 1.0)
ax.set_title("Per-Fold Accuracy (All Configs)")
save("fold_variance_new.png", fig)
print("4/5 fold variance done")

# ── 5. Copy confusion matrix ────────────────────────────────────────────────
copy_img(
    "/home/dat/dev/mycoai_projects/results/cross_validation/fold0_E2_freq_strength_k7/confusion_matrix.png",
    "confusion_matrix_cv_best.png",
)
print("5/5 confusion matrix copied")

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n=== RESULTS SUMMARY ===")
print(
    f"CV: {top6.iloc[0]['media_strategy']} {top6.iloc[0]['agg_strategy']} k{top6.iloc[0]['k']} = {top6.iloc[0]['mean_accuracy']:.3f}"
)
print(f"Segmentation: YOLO={yolo_acc:.3f}, KMeans={kmeans_acc:.3f}")
print("Best retrieval chart uses EfficientNetB1 fine-tuned, E1, freq_strength, K=5")
