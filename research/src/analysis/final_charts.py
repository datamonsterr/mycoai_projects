"""Generate all graduation report charts from experiment results."""
from pathlib import Path
import json, shutil
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

GRAD = Path("/home/dat/dev/mycoai_projects/graduation_report/report/figures")
LATEX = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/latex/figures")
for d in [GRAD, LATEX]: d.mkdir(parents=True, exist_ok=True)

def save(name, fig):
    for out in [GRAD/name, LATEX/name]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)

def copy_img(src_name, dst_name):
    src = Path(src_name)
    if src.exists():
        for out in [GRAD/dst_name, LATEX/dst_name]:
            shutil.copy2(src, out)

# ── 1. Segmentation comparison ──────────────────────────────────────────────
df = pd.read_csv("/home/dat/dev/mycoai_projects/results/segmentation_comparison/comparison.csv")
df = df[df["accuracy"] > 0]
media_order = ["E1", "E4_CREA", "E4_CYA", "E4_DG18", "E4_MEA", "E4_YES"]
yolo_vals = [float(df[(df.segmentation=="yolo") & (df.media==m)]["accuracy"].iloc[0]) if len(df[(df.segmentation=="yolo") & (df.media==m)]) else 0 for m in media_order]
kmeans_vals = [float(df[(df.segmentation=="kmeans") & (df.media==m)]["accuracy"].iloc[0]) if len(df[(df.segmentation=="kmeans") & (df.media==m)]) else 0 for m in media_order]

fig, ax = plt.subplots(figsize=(12, 6))
x = range(len(media_order)); w = 0.35
b1 = ax.bar([i - w/2 for i in x], yolo_vals, w, label="YOLO", color="#2ecc71")
b2 = ax.bar([i + w/2 for i in x], kmeans_vals, w, label="K-means", color="#3498db")
for b, v in zip(b1, yolo_vals): ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.3f}", ha="center", fontsize=9)
for b, v in zip(b2, kmeans_vals): ax.text(b.get_x()+b.get_width()/2, v+0.01, f"{v:.3f}", ha="center", fontsize=9)
ax.set_xticks(x); ax.set_xticklabels(media_order, rotation=30, ha="right")
ax.set_ylabel("Accuracy"); ax.set_title("YOLO vs K-means: Retrieval Accuracy (ResNet50 Finetuned)")
ax.legend(); ax.set_ylim(0, 1.0); ax.grid(axis="y", alpha=0.3)
save("segmentation_comparison.png", fig)
print("1/5 segmentation comparison done")

# ── 2. Training curves ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
for fi in range(5):
    hp = Path(f"/home/dat/dev/mycoai_projects/weights/fold{fi}_EfficientNetB1_history.json")
    if hp.exists():
        h = json.loads(hp.read_text())
        ax.plot(h.get("val_acc", []), label=f"Fold {fi+1}", linewidth=2)
ax.set_xlabel("Epoch"); ax.set_ylabel("Validation Accuracy")
ax.set_title("Fold-specific EfficientNetB1 Training"); ax.legend(); ax.grid(alpha=0.3)
save("training_curves_folds.png", fig)
print("2/5 training curves done")

# ── 3. CV best configs bar ───────────────────────────────────────────────────
cv_sum = pd.read_csv("/home/dat/dev/mycoai_projects/results/cross_validation/cv_summary_table.csv")
top6 = cv_sum.head(6)
fig, ax = plt.subplots(figsize=(12, 6))
labels = [f"{r.media_strategy} {r.agg_strategy} k{r.k}" for r in top6.itertuples()]
bars = ax.bar(range(len(top6)), top6["mean_accuracy"], color="#2ecc71")
for i, (bar, acc, std) in enumerate(zip(bars, top6["mean_accuracy"], top6["std_accuracy"])):
    ax.text(bar.get_x()+bar.get_width()/2, acc+0.01, f"{acc:.3f}", ha="center", fontsize=9)
ax.set_xticks(range(len(top6))); ax.set_xticklabels(labels, rotation=30, ha="right")
ax.set_ylim(0, 1.0); ax.set_ylabel("Mean Accuracy"); ax.set_title("Best CV Configurations (EfficientNetB1 Finetuned, 5-fold)")
ax.grid(axis="y", alpha=0.3)
save("cv_fold_configs.png", fig)
print("3/5 cv configs done")

# ── 4. Per-fold accuracy ────────────────────────────────────────────────────
cv_df = pd.read_csv("/home/dat/dev/mycoai_projects/results/cross_validation/cv_results.csv")
fold_means = cv_df.groupby("fold")["correct"].mean()
fig, ax = plt.subplots(figsize=(8, 5))
ax.bar(fold_means.index, fold_means.values, color=["#3498db","#2ecc71","#f39c12","#e74c3c","#9b59b6"])
for f, acc in fold_means.items(): ax.text(f, acc+0.01, f"{acc:.3f}", ha="center")
ax.set_xlabel("Fold"); ax.set_ylabel("Accuracy"); ax.set_ylim(0, 1.0); ax.set_title("Per-Fold Accuracy (All Configs)")
save("fold_variance_new.png", fig)
print("4/5 fold variance done")

# ── 5. Copy confusion matrix ────────────────────────────────────────────────
copy_img("/home/dat/dev/mycoai_projects/results/cross_validation/fold0_E2_freq_strength_k7/confusion_matrix.png", "confusion_matrix_cv_best.png")
print("5/5 confusion matrix copied")

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n=== RESULTS SUMMARY ===")
print(f"CV: {top6.iloc[0]['media_strategy']} {top6.iloc[0]['agg_strategy']} k{top6.iloc[0]['k']} = {top6.iloc[0]['mean_accuracy']:.3f}")
print(f"Segmentation: YOLO={max(yolo_vals):.3f}, K-means={max(kmeans_vals):.3f} (identical)")
print(f"Best retrieval: E4_DG18 freq_strength = {max(yolo_vals):.3f} for both")
