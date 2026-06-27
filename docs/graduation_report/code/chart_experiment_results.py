"""Generate all experiment charts for graduation report.
Usage: uv --directory research run python docs/graduation_report/code/chart_experiment_results.py
"""
import csv
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/latex/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STYLE = {"font.family": "serif", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8}
plt.rcParams.update(STYLE)

RESULTS = Path("/home/dat/dev/mycoai_projects/results")
YOLO_DIR = RESULTS / "retrieval_k7_yolo_local"
KMEANS_DIR = RESULTS / "retrieval_k7_kmeans_local"
PIPE_CSV = RESULTS / "retrieval_pipeline_comparison.csv"
THRESH_CSV = Path("/home/dat/dev/mycoai_projects/results/threshold/log/all_experiments.csv")
SEG_CSV = Path("/home/dat/dev/mycoai_projects/results/segmentation_comparison/comparison.csv")


def load_prediction_reports(root: Path):
    rows = []
    for txt in root.glob('*/prediction_report_*.txt'):
        content = txt.read_text(errors='ignore') if txt.exists() else ''
        import re
        match = re.search(r'Accuracy:\s*([0-9.]+)', content)
        if not match:
            continue
        acc = float(match.group(1))
        name = txt.parent.name
        rows.append({
            'name': name,
            'accuracy': acc,
            'extractor': name.rsplit('_', 2)[0],
            'strategy': 'freq_strength' if 'freq_strength' in name else 'weighted',
            'environment': 'E1' if name.endswith('_E1') else 'E2',
        })
    return rows


def save(fig, name):
    out = OUTPUT_DIR / name
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"  {name}")


# ═══════════════════════════════════════════════════════════════════════════
# 1. FEATURE EXTRACTOR COMPARISON (sorted, freq_strength + E1, K=7)
# ═══════════════════════════════════════════════════════════════════════════
def chart_extractor_comparison():
    valid = load_prediction_reports(YOLO_DIR)
    agg = 'freq_strength'
    env = 'E1'
    extractor_configs = [
        ('resnet50_finetuned', 'ResNet50 (FT)', '#1f77b4'),
        ('efficientnetb1_finetuned', 'EfficientNetB1 (FT)', '#1f77b4'),
        ('mobilenetv2_finetuned', 'MobileNetV2 (FT)', '#1f77b4'),
        ('resnet50', 'ResNet50 (PT)', '#ff7f0e'),
        ('efficientnetb1', 'EfficientNetB1 (PT)', '#ff7f0e'),
        ('mobilenetv2', 'MobileNetV2 (PT)', '#ff7f0e'),
        ('colorhistogram', 'ColorHistogram (TR)', '#2ca02c'),
        ('colorhistogramhs', 'ColorHistogramHS (TR)', '#2ca02c'),
        ('hog', 'HOG (TR)', '#2ca02c'),
        ('gabor', 'Gabor (TR)', '#2ca02c'),
    ]
    results = []
    for ext_name, label, color in extractor_configs:
        matched = [r for r in valid if r['name'] == f'{ext_name}_{agg}_{env}']
        acc = matched[0]['accuracy'] * 100 if matched else 0.0
        results.append((label, acc, color))
    results.sort(key=lambda x: x[1], reverse=True)

    labels, scores, colors = zip(*results)
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(range(len(labels)), scores, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7, rotation=25, ha='right')
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Latest YOLO Retrieval: Feature Extractor Comparison (freq_strength, E1, K=7)')
    ax.set_ylim(0, max(scores) * 1.2 if max(scores) > 0 else 100)
    for bar, score in zip(bars, scores):
        if score > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{score:.1f}%', ha='center', va='bottom', fontsize=7, fontweight='bold')
    ax.legend(handles=[
        Patch(facecolor='#1f77b4', label='Fine-tuned DL'),
        Patch(facecolor='#ff7f0e', label='Pretrained DL'),
        Patch(facecolor='#2ca02c', label='Traditional'),
    ], loc='upper right', fontsize=7)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save(fig, 'extractor_comparison.png')


# ═══════════════════════════════════════════════════════════════════════════
# 2. RETRIEVAL FAMILY COMPARISON (top by extractor family)
# ═══════════════════════════════════════════════════════════════════════════
def chart_retrieval_top():
    valid = [r for r in load_prediction_reports(YOLO_DIR) if r['strategy'] == 'freq_strength']
    finetuned = sorted([r for r in valid if 'finetuned' in r['extractor']], key=lambda r: -r['accuracy'])[:5]
    pretrained = sorted([r for r in valid if 'finetuned' not in r['extractor']
                          and any(x in r['extractor'] for x in ['resnet50', 'efficientnetb1', 'mobilenetv2'])], key=lambda r: -r['accuracy'])[:5]
    traditional = sorted([r for r in valid if any(x in r['extractor'] for x in ['colorhistogram', 'hog', 'gabor'])], key=lambda r: -r['accuracy'])[:5]
    all_top = finetuned + pretrained + traditional
    if not all_top: return

    names = [r['name'].replace('_freq_strength_', '\n') for r in all_top]
    accs = [r['accuracy'] * 100 for r in all_top]
    colors = ['#1f77b4'] * len(finetuned) + ['#ff7f0e'] * len(pretrained) + ['#2ca02c'] * len(traditional)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh(range(len(all_top)), accs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(range(len(all_top)))
    ax.set_yticklabels(names, fontsize=5.5)
    ax.set_xlabel('Accuracy (%)')
    ax.set_title('Latest YOLO Top Retrieval Configurations by Extractor Family (freq_strength, K=7)')
    ax.invert_yaxis()
    for i, acc in enumerate(accs):
        ax.text(acc + 0.3, i, f'{acc:.1f}%', va='center', fontsize=5.5)
    ax.legend(handles=[
        Patch(facecolor='#1f77b4', label='Fine-tuned DL'),
        Patch(facecolor='#ff7f0e', label='Pretrained DL'),
        Patch(facecolor='#2ca02c', label='Traditional'),
    ], loc='lower right', fontsize=7)
    fig.tight_layout()
    save(fig, 'retrieval_family_comparison.png')


def chart_kmeans_vs_yolo_latest():
    yolo_rows = load_prediction_reports(YOLO_DIR)
    kmeans_rows = load_prediction_reports(KMEANS_DIR)
    labels = [
        ('efficientnetb1_finetuned_freq_strength_E1', 'EffB1 FT / FS / E1'),
        ('mobilenetv2_finetuned_weighted_E1', 'MobV2 FT / W / E1'),
        ('resnet50_finetuned_weighted_E1', 'ResNet50 FT / W / E1'),
        ('efficientnetb1_freq_strength_E1', 'EffB1 PT / FS / E1'),
        ('mobilenetv2_freq_strength_E1', 'MobV2 PT / FS / E1'),
        ('resnet50_weighted_E1', 'ResNet50 PT / W / E1'),
    ]
    paired = []
    for key, label in labels:
        y = next((r['accuracy'] * 100 for r in yolo_rows if r['name'] == key), 0.0)
        k = next((r['accuracy'] * 100 for r in kmeans_rows if r['name'] == key), 0.0)
        paired.append((label, y, k))
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = range(len(paired)); w = 0.36
    yolo_bars = ax.bar([i - w/2 for i in x], [p[1] for p in paired], w, label='YOLO segments', color='#2ecc71')
    kmeans_bars = ax.bar([i + w/2 for i in x], [p[2] for p in paired], w, label='K-means segments', color='#3498db')
    ax.set_xticks(list(x)); ax.set_xticklabels([p[0] for p in paired], rotation=25, ha='right', fontsize=7)
    ax.set_ylabel('Accuracy (%)')
    ax.set_title('Latest Retrieval Accuracy: YOLO vs K-means Segment Sources')
    for bars in [yolo_bars, kmeans_bars]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f'{h:.1f}', ha='center', va='bottom', fontsize=6.5)
    ax.set_ylim(0, max(max(p[1], p[2]) for p in paired) * 1.25 if paired else 100)
    ax.legend(fontsize=7)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    save(fig, 'kmeans_vs_yolo_latest.png')


# ═══════════════════════════════════════════════════════════════════════════
# 3. CROSS-VALIDATION HEATMAPS
# ═══════════════════════════════════════════════════════════════════════════
def chart_cv_heatmaps():
    cv_csv = Path("/home/dat/dev/mycoai_projects/results/cross_validation/cv_summary_table.csv")
    rows = list(csv.DictReader(open(cv_csv)))
    data = defaultdict(list)
    for r in rows:
        key = (r['media_strategy'], r['agg_strategy'], int(r['k']))
        data[key].append(float(r['mean_accuracy']))
    agg_data = {}
    for (media, agg, k), accs in data.items():
        agg_data[(media, agg, k)] = np.mean(accs)
    media_vals = sorted(set(m for m, _, _ in agg_data))
    k_vals = sorted(set(k for _, _, k in agg_data))
    agg_vals = sorted(set(a for _, a, _ in agg_data))

    # Heatmap: K vs media_strategy (one per agg)
    for agg in agg_vals:
        mat = np.zeros((len(media_vals), len(k_vals)))
        for i, m in enumerate(media_vals):
            for j, k in enumerate(k_vals):
                mat[i, j] = agg_data.get((m, agg, k), 0) * 100
        fig, ax = plt.subplots(figsize=(6, 2.2))
        im = ax.imshow(mat, cmap='YlOrRd', aspect='auto', vmin=mat.min()*0.95, vmax=mat.max()*1.02)
        ax.set_xticks(range(len(k_vals))); ax.set_xticklabels([f'k={k}' for k in k_vals])
        ax.set_yticks(range(len(media_vals))); ax.set_yticklabels(media_vals, fontsize=7)
        for i in range(len(media_vals)):
            for j in range(len(k_vals)):
                ax.text(j, i, f'{mat[i,j]:.1f}', ha='center', va='center', fontsize=6,
                        color='black' if mat[i,j] < 75 else 'white')
        ax.set_title(f'CV Accuracy: {agg} Aggregation')
        plt.colorbar(im, ax=ax, label='Accuracy %')
        fig.tight_layout()
        save(fig, f'cv_heatmap_{agg}_k_vs_media.png')

    # Heatmap: aggregation vs K (mean across media)
    mat2 = np.zeros((len(agg_vals), len(k_vals)))
    for i, a in enumerate(agg_vals):
        for j, k in enumerate(k_vals):
            vs = [agg_data[(m, a, k)] for m in media_vals if (m, a, k) in agg_data]
            mat2[i, j] = (np.mean(vs) * 100) if vs else 0
    fig, ax = plt.subplots(figsize=(6, 3))
    im = ax.imshow(mat2, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(k_vals))); ax.set_xticklabels([f'k={k}' for k in k_vals])
    ax.set_yticks(range(len(agg_vals))); ax.set_yticklabels(agg_vals)
    for i in range(len(agg_vals)):
        for j in range(len(k_vals)):
            ax.text(j, i, f'{mat2[i,j]:.1f}%', ha='center', va='center', fontsize=7,
                    color='black' if mat2[i,j] < 75 else 'white')
    ax.set_title('CV Accuracy: Aggregation vs K (mean across environments)')
    plt.colorbar(im, ax=ax, label='Accuracy %')
    fig.tight_layout()
    save(fig, 'cv_heatmap_agg_vs_k.png')

    # Heatmap: media vs aggregation (mean across K)
    mat3 = np.zeros((len(media_vals), len(agg_vals)))
    for i, m in enumerate(media_vals):
        for j, a in enumerate(agg_vals):
            vs = [agg_data[(m, a, k)] for k in k_vals if (m, a, k) in agg_data]
            mat3[i, j] = (np.mean(vs) * 100) if vs else 0
    fig, ax = plt.subplots(figsize=(7, 2.8))
    im = ax.imshow(mat3, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(agg_vals))); ax.set_xticklabels(agg_vals, fontsize=7, rotation=30, ha='right')
    ax.set_yticks(range(len(media_vals))); ax.set_yticklabels(media_vals, fontsize=7)
    for i in range(len(media_vals)):
        for j in range(len(agg_vals)):
            ax.text(j, i, f'{mat3[i,j]:.1f}', ha='center', va='center', fontsize=6.5,
                    color='black' if mat3[i,j] < 75 else 'white')
    ax.set_title('CV Accuracy: Environment vs Aggregation (mean across K)')
    plt.colorbar(im, ax=ax, label='Accuracy %')
    fig.tight_layout()
    save(fig, 'cv_heatmap_media_vs_agg.png')


# ═══════════════════════════════════════════════════════════════════════════
# 4. CONFUSION MATRICES
# ═══════════════════════════════════════════════════════════════════════════
def chart_confusion_matrices():
    yolo_rows = load_prediction_reports(YOLO_DIR)

    def copy_confusion(config_name, filename):
        src = YOLO_DIR / config_name / 'confusion_matrix.png'
        if src.exists():
            import shutil
            shutil.copy2(src, OUTPUT_DIR / filename)
            print(f'  {filename}')

    ft = [r for r in yolo_rows if 'finetuned' in r['name'] and r['strategy'] == 'freq_strength']
    pt = [r for r in yolo_rows if 'finetuned' not in r['name'] and any(x in r['name'] for x in ['resnet50', 'efficientnetb1', 'mobilenetv2']) and r['strategy'] == 'freq_strength']
    trad = [r for r in yolo_rows if any(x in r['name'] for x in ['hog', 'gabor', 'colorhistogram']) and r['strategy'] == 'freq_strength']
    if ft:
        copy_confusion(max(ft, key=lambda r: r['accuracy'])['name'], 'confusion_best_finetuned.png')
        copy_confusion(min(ft, key=lambda r: r['accuracy'])['name'], 'confusion_worst_finetuned.png')
    if pt:
        copy_confusion(max(pt, key=lambda r: r['accuracy'])['name'], 'confusion_best_pretrained.png')
    if trad:
        copy_confusion(max(trad, key=lambda r: r['accuracy'])['name'], 'confusion_best_traditional.png')


# ═══════════════════════════════════════════════════════════════════════════
# 5. THRESHOLD TOP BAR CHART
# ═══════════════════════════════════════════════════════════════════════════
def chart_threshold_top():
    if not THRESH_CSV.exists(): return
    rows = list(csv.DictReader(open(THRESH_CSV)))
    top = sorted(rows, key=lambda r: -float(r.get('f1', 0)))[:12]
    names = [f"{r['formula']}\n{r['algorithm']}" for r in top]
    f1s = [float(r['f1']) * 100 for r in top]
    precs = [float(r['precision']) * 100 for r in top]
    recalls = [float(r['recall']) * 100 for r in top]
    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(top)); w = 0.25
    ax.bar([i - w for i in x], f1s, w, label='F1', color='#1f77b4', edgecolor='white', linewidth=0.3)
    ax.bar(x, precs, w, label='Precision', color='#ff7f0e', edgecolor='white', linewidth=0.3)
    ax.bar([i + w for i in x], recalls, w, label='Recall', color='#2ca02c', edgecolor='white', linewidth=0.3)
    ax.set_xticks(x); ax.set_xticklabels(names, fontsize=5.5, rotation=30, ha='right')
    ax.set_ylabel('%'); ax.set_title('Top Threshold Strategies (F1, Precision, Recall)')
    ax.legend(fontsize=7)
    fig.tight_layout()
    save(fig, 'threshold_top_bar.png')


if __name__ == "__main__":
    print("Generating charts...")
    chart_extractor_comparison()
    chart_retrieval_top()
    chart_kmeans_vs_yolo_latest()
    chart_cv_heatmaps()
    chart_confusion_matrices()
    chart_threshold_top()
    print("Done.")
