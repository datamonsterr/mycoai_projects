"""Generate charts for graduation report from experiment results."""
import json
import csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path
from collections import defaultdict

OUTPUT_DIR = Path("/home/dat/dev/mycoai_projects/docs/graduation_report/latex/figures")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STYLE = {"font.family": "serif", "font.size": 8, "axes.titlesize": 9, "axes.labelsize": 8}
plt.rcParams.update(STYLE)

RESULTS = Path("/home/dat/dev/mycoai_projects/results")
CV_CSV = Path("/home/dat/dev/mycoai_projects/results/cross_validation/cv_summary_table.csv")
PIPE_CSV = Path("/home/dat/dev/mycoai_projects/results/retrieval_pipeline_comparison.csv")
THRESH_JSON = Path("/home/dat/dev/mycoai_projects/results/threshold/threshold_summary.json")
THRESH_CSV = Path("/home/dat/dev/mycoai_projects/results/threshold/log/all_experiments.csv")
SEG_CSV = Path("/home/dat/dev/mycoai_projects/results/segmentation_comparison/comparison.csv")

# ─── 1. FEATURE EXTRACTOR COMPARISON COLUMN CHART ───
def chart_extractor_comparison():
    """Column chart: finetuned DL vs pretrained DL vs traditional, same settings."""
    rows = list(csv.DictReader(open(PIPE_CSV)))
    valid = [r for r in rows if r['accuracy'] and r['accuracy'].strip()]

    # Use a controlled setting: weighted, E1 for fair comparison
    target_agg = 'weighted'
    target_env = 'E1'

    extractor_order = [
        ('resnet50_finetuned', 'ResNet50\n(FT)', '#1f77b4'),
        ('efficientnetb1_finetuned', 'EfficientNetB1\n(FT)', '#1f77b4'),
        ('mobilenetv2_finetuned', 'MobileNetV2\n(FT)', '#1f77b4'),
        ('resnet50', 'ResNet50\n(PT)', '#ff7f0e'),
        ('efficientnetb1', 'EfficientNetB1\n(PT)', '#ff7f0e'),
        ('mobilenetv2', 'MobileNetV2\n(PT)', '#ff7f0e'),
        ('colorhistogram', 'ColorHist\n(TR)', '#2ca02c'),
        ('colorhistogramhs', 'ColorHistHS\n(TR)', '#2ca02c'),
        ('hog', 'HOG\n(TR)', '#2ca02c'),
        ('gabor', 'Gabor\n(TR)', '#2ca02c'),
    ]

    scores = []
    labels = []
    colors = []
    for ext_name, label, color in extractor_order:
        match_name = f"{ext_name}_{target_agg}_{target_env}"
        matched = [r for r in valid if r['name'] == match_name]
        if matched:
            acc = float(matched[0]['accuracy'])
        else:
            acc = 0.0
        scores.append(acc * 100)
        labels.append(label)
        colors.append(color)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.bar(range(len(labels)), scores, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel('Accuracy (%)')
    ax.set_title(f'Feature Extractor Comparison ({target_agg.capitalize()} Aggregation, {target_env} Environment, K=5)')
    ax.set_ylim(0, max(scores) * 1.25)

    for bar, score in zip(bars, scores):
        if score > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
                    f'{score:.1f}%', ha='center', va='bottom', fontsize=6.5)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#1f77b4', label='Fine-tuned DL'),
        Patch(facecolor='#ff7f0e', label='Pretrained DL'),
        Patch(facecolor='#2ca02c', label='Traditional'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=7)

    fig.tight_layout()
    out = OUTPUT_DIR / "extractor_comparison.png"
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


# ─── 2. CROSS-VALIDATION HEATMAPS ───
def chart_cv_heatmaps():
    """Heatmaps: K vs media_strategy, K vs aggregation, media vs aggregation."""
    rows = list(csv.DictReader(open(CV_CSV)))
    data = defaultdict(list)
    for r in rows:
        key = (r['media_strategy'], r['agg_strategy'], int(r['k']))
        data[key].append(float(r['mean_accuracy']))

    # Aggregate mean
    agg_data = {}
    for (media, agg, k), accs in data.items():
        agg_data[(media, agg, k)] = np.mean(accs)

    # (a) K vs media_strategy
    media_vals = sorted(set(m for m,_,_ in agg_data))
    k_vals = sorted(set(k for _,_,k in agg_data))
    for agg in sorted(set(a for _,a,_ in agg_data)):
        mat = np.zeros((len(media_vals), len(k_vals)))
        for i, m in enumerate(media_vals):
            for j, k in enumerate(k_vals):
                mat[i, j] = agg_data.get((m, agg, k), 0) * 100

        fig, ax = plt.subplots(figsize=(6, 2.2))
        im = ax.imshow(mat, cmap='YlOrRd', aspect='auto', vmin=mat.min()*0.95, vmax=mat.max()*1.02)
        ax.set_xticks(range(len(k_vals)))
        ax.set_xticklabels([f'k={k}' for k in k_vals])
        ax.set_yticks(range(len(media_vals)))
        ax.set_yticklabels(media_vals, fontsize=7)
        for i in range(len(media_vals)):
            for j in range(len(k_vals)):
                ax.text(j, i, f'{mat[i,j]:.1f}', ha='center', va='center', fontsize=6, color='black' if mat[i,j] < 75 else 'white')
        ax.set_title(f'CV Accuracy: {agg} Aggregation')
        plt.colorbar(im, ax=ax, label='Accuracy %')
        fig.tight_layout()
        out = OUTPUT_DIR / f"cv_heatmap_{agg}_k_vs_media.png"
        fig.savefig(out, dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved: {out}")

    # (b) Single combined heatmap: K vs aggregation (mean across media)
    agg_vals = sorted(set(a for _,a,_ in agg_data))
    mat2 = np.zeros((len(agg_vals), len(k_vals)))
    for i, a in enumerate(agg_vals):
        for j, k in enumerate(k_vals):
            vals = [agg_data[(m, a, k)] for m in media_vals if (m, a, k) in agg_data]
            mat2[i, j] = (np.mean(vals) * 100) if vals else 0

    fig, ax = plt.subplots(figsize=(6, 3))
    im = ax.imshow(mat2, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(k_vals)))
    ax.set_xticklabels([f'k={k}' for k in k_vals])
    ax.set_yticks(range(len(agg_vals)))
    ax.set_yticklabels(agg_vals)
    for i in range(len(agg_vals)):
        for j in range(len(k_vals)):
            ax.text(j, i, f'{mat2[i,j]:.1f}%', ha='center', va='center', fontsize=7,
                    color='black' if mat2[i,j] < 75 else 'white')
    ax.set_title('CV Accuracy: Aggregation Strategy vs K (mean across environments)')
    plt.colorbar(im, ax=ax, label='Accuracy %')
    fig.tight_layout()
    out = OUTPUT_DIR / "cv_heatmap_agg_vs_k.png"
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")

    # (c) Heatmap: media vs aggregation (mean across K)
    mat3 = np.zeros((len(media_vals), len(agg_vals)))
    for i, m in enumerate(media_vals):
        for j, a in enumerate(agg_vals):
            vals = [agg_data[(m, a, k)] for k in k_vals if (m, a, k) in agg_data]
            mat3[i, j] = (np.mean(vals) * 100) if vals else 0

    fig, ax = plt.subplots(figsize=(7, 2.8))
    im = ax.imshow(mat3, cmap='YlOrRd', aspect='auto')
    ax.set_xticks(range(len(agg_vals)))
    ax.set_xticklabels(agg_vals, fontsize=7, rotation=30, ha='right')
    ax.set_yticks(range(len(media_vals)))
    ax.set_yticklabels(media_vals, fontsize=7)
    for i in range(len(media_vals)):
        for j in range(len(agg_vals)):
            ax.text(j, i, f'{mat3[i,j]:.1f}', ha='center', va='center', fontsize=6.5,
                    color='black' if mat3[i,j] < 75 else 'white')
    ax.set_title('CV Accuracy: Environment Strategy vs Aggregation (mean across K)')
    plt.colorbar(im, ax=ax, label='Accuracy %')
    fig.tight_layout()
    out = OUTPUT_DIR / "cv_heatmap_media_vs_agg.png"
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


# ─── 3. CONFUSION MATRICES ───
def chart_confusion_matrices():
    """Generate confusion matrices by reading evaluation_results.json files."""
    import re
    pipe_dir = RESULTS / "retrieval_pipeline"

    # Find best and worst configs for each category
    rows = list(csv.DictReader(open(PIPE_CSV)))
    valid = [r for r in rows if r['accuracy'] and r['accuracy'].strip()]

    species_order = [
        'Penicillium polonicum',
        'Penicillium melanoconidium',
        'Penicillium freii',
        'Penicillium viridicatum',
        'Penicillium tricolor',
        'Penicillium neoechinulatum',
        'Penicillium aurantiogriseum',
    ]
    species_short = ['polonicum', 'melanocon.', 'freii', 'viridicatum',
                     'tricolor', 'neoechinul.', 'aurantiogr.']

    def load_confusion(config_name):
        eval_path = pipe_dir / config_name / "evaluation_results.json"
        if not eval_path.exists():
            return None
        with open(eval_path) as f:
            data = json.load(f)
        matrix = np.zeros((len(species_order), len(species_order)))
        for r in data.get('results', []):
            gt = r.get('ground_truth', '')
            pred = r.get('predicted_specy', '')
            if gt in species_order and pred in species_order:
                matrix[species_order.index(gt), species_order.index(pred)] += 1
        acc = data.get('overall_accuracy', 0)
        return matrix, acc, f"{data.get('correct_predictions', 0)}/{data.get('total_strains', 0)}"

    def plot_confusion(cm_tuple, filename, title_prefix=""):
        matrix, acc, label = cm_tuple
        fig, ax = plt.subplots(figsize=(5.5, 5))
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        norm = matrix / row_sums
        im = ax.imshow(norm, cmap='Blues', vmin=0, vmax=1, aspect='auto')
        ax.set_xticks(range(len(species_short)))
        ax.set_yticks(range(len(species_short)))
        ax.set_xticklabels(species_short, rotation=45, ha='right', fontsize=6.5)
        ax.set_yticklabels(species_short, fontsize=6.5)
        ax.set_xlabel('Predicted')
        ax.set_ylabel('Ground Truth')

        for i in range(len(species_order)):
            for j in range(len(species_order)):
                count = int(matrix[i, j])
                pct = norm[i, j]
                color = 'white' if pct > 0.55 else 'black'
                if count > 0:
                    ax.text(j, i, f'{count}\n({pct:.0%})', ha='center', va='center',
                            fontsize=5.5, color=color, fontweight='bold' if i == j else 'normal')

        title = f'{title_prefix}{label}\nAccuracy: {acc:.1%}'
        ax.set_title(title, fontsize=8)
        plt.colorbar(im, ax=ax, label='Fraction')
        fig.tight_layout()
        out = OUTPUT_DIR / filename
        fig.savefig(out, dpi=200, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved: {out}")

    # Best finetuned DL
    ft = [r for r in valid if 'finetuned' in r['name'] and 'freq_strength' in r['name']]
    if ft:
        best_ft = max(ft, key=lambda r: float(r['accuracy']))
        cm = load_confusion(best_ft['name'])
        if cm is not None:
            plot_confusion(cm, "confusion_best_finetuned.png", "Best Fine-tuned: ")

    # Best pretrained DL
    pt = [r for r in valid if 'finetuned' not in r['name']
          and any(x in r['name'] for x in ['resnet50', 'efficientnetb1', 'mobilenetv2'])
          and 'freq_strength' in r['name']]
    if pt:
        best_pt = max(pt, key=lambda r: float(r['accuracy']))
        cm = load_confusion(best_pt['name'])
        if cm is not None:
            plot_confusion(cm, "confusion_best_pretrained.png", "Best Pretrained: ")

    # Best traditional
    trad = [r for r in valid if any(x in r['name'] for x in ['hog', 'gabor', 'colorhistogram'])
            and 'freq_strength' in r['name']]
    if trad:
        best_trad = max(trad, key=lambda r: float(r['accuracy']))
        cm = load_confusion(best_trad['name'])
        if cm is not None:
            plot_confusion(cm, "confusion_best_traditional.png", "Best Traditional: ")

    # Worst finetuned
    if ft:
        worst_ft = min(ft, key=lambda r: float(r['accuracy']))
        cm = load_confusion(worst_ft['name'])
        if cm is not None:
            plot_confusion(cm, "confusion_worst_finetuned.png", "Worst Fine-tuned: ")

    # Segmentation best confusion
    seg_rows = list(csv.DictReader(open(SEG_CSV)))
    if seg_rows:
        best_seg = max(seg_rows, key=lambda r: float(r['accuracy']))
        seg_name = best_seg['config']
        cm = load_confusion(seg_name)
        if cm is not None:
            plot_confusion(cm, "confusion_best_segmentation.png", "Best Segmentation: ")


# ─── 4. RETRIEVAL TOP N BAR CHART ───
def chart_retrieval_top():
    """Top retrieval configs by accuracy, per category."""
    rows = list(csv.DictReader(open(PIPE_CSV)))
    valid = [r for r in rows if r['accuracy'] and r['accuracy'].strip()
             and 'freq_strength' in r['name']]

    # Group by extractor category
    finetuned = sorted([r for r in valid if 'finetuned' in r['name']],
                       key=lambda r: -float(r['accuracy']))[:5]
    pretrained = sorted([r for r in valid if 'finetuned' not in r['name']
                         and any(x in r['name'] for x in ['resnet50_', 'efficientnetb1_', 'mobilenetv2_'])
                         and '_freq_strength' in r['name']],
                        key=lambda r: -float(r['accuracy']))[:5]
    traditional = sorted([r for r in valid if any(x in r['name']
                          for x in ['colorhistogram_', 'hog_', 'gabor_'])
                          and '_freq_strength' in r['name']],
                         key=lambda r: -float(r['accuracy']))[:5]

    all_top = finetuned + pretrained + traditional
    if not all_top:
        return

    names = [r['name'].replace('_freq_strength_', '\n') for r in all_top]
    accs = [float(r['accuracy']) * 100 for r in all_top]
    cats = (['Fine-tuned'] * len(finetuned) + ['Pretrained'] * len(pretrained)
            + ['Traditional'] * len(traditional))
    colors = ['#1f77b4'] * len(finetuned) + ['#ff7f0e'] * len(pretrained) + ['#2ca02c'] * len(traditional)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    y_pos = range(len(all_top))
    bars = ax.barh(y_pos, accs, color=colors, edgecolor='white', linewidth=0.5)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=5.5)
    ax.set_xlabel('Accuracy (%)')
    ax.set_title('Top Retrieval Configurations by Extractor Family (freq_strength, K=5)')
    ax.invert_yaxis()

    for bar, acc in zip(bars, accs):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                f'{acc:.1f}%', va='center', fontsize=5.5)

    from matplotlib.patches import Patch
    ax.legend(handles=[
        Patch(facecolor='#1f77b4', label='Fine-tuned DL'),
        Patch(facecolor='#ff7f0e', label='Pretrained DL'),
        Patch(facecolor='#2ca02c', label='Traditional'),
    ], loc='lower right', fontsize=7)

    fig.tight_layout()
    out = OUTPUT_DIR / "retrieval_family_comparison.png"
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


# ─── 5. THRESHOLD TOP CHART ───
def chart_threshold_top():
    """Top threshold strategies bar chart."""
    if not THRESH_CSV.exists():
        return
    rows = list(csv.DictReader(open(THRESH_CSV)))
    top = sorted(rows, key=lambda r: -float(r.get('f1', 0)))[:12]

    names = [f"{r['formula']}\n{r['algorithm']}" for r in top]
    f1s = [float(r['f1']) * 100 for r in top]
    precs = [float(r['precision']) * 100 for r in top]
    recalls = [float(r['recall']) * 100 for r in top]

    fig, ax = plt.subplots(figsize=(8, 4))
    x = range(len(top))
    w = 0.25
    ax.bar([i - w for i in x], f1s, w, label='F1', color='#1f77b4', edgecolor='white', linewidth=0.3)
    ax.bar(x, precs, w, label='Precision', color='#ff7f0e', edgecolor='white', linewidth=0.3)
    ax.bar([i + w for i in x], recalls, w, label='Recall', color='#2ca02c', edgecolor='white', linewidth=0.3)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=5.5, rotation=30, ha='right')
    ax.set_ylabel('%')
    ax.set_title('Top Threshold Strategies (F1, Precision, Recall)')
    ax.legend(fontsize=7)
    fig.tight_layout()
    out = OUTPUT_DIR / "threshold_top_bar.png"
    fig.savefig(out, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


if __name__ == "__main__":
    print("Generating charts...")
    chart_extractor_comparison()
    chart_cv_heatmaps()
    chart_confusion_matrices()
    chart_retrieval_top()
    chart_threshold_top()
    print("Done.")
