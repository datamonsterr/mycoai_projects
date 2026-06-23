# Graduation Report — Build & Update Workflow

## Directory Structure

```
docs/graduation_report/
├── README.md              # This file
├── code/                  # Chart generation scripts (Python)
│   └── chart_experiment_results.py   # All experiment charts
└── latex/                 # LaTeX report source
    ├── main.tex           # Root document
    ├── Chapter/           # Chapter .tex files
    ├── figures/           # All image assets (PNG, JPG, PDF)
    ├── reference.bib      # BibTeX references
    └── main.pdf           # Compiled output
```

## Chart Generation

### Source Scripts

| Script | Purpose |
|--------|---------|
| `code/chart_experiment_results.py` | Feature extractor comparison, CV heatmaps, confusion matrices, retrieval top-N, threshold bars |
| `research/src/analysis/final_charts.py` | Segmentation comparison, training curves, CV best configs, fold variance |
| `research/src/analysis/graduation_report_assets.py` | CV model comparison, fold variance, threshold charts |
| `research/src/analysis/threshold_known_distribution.py` | Threshold known-vs-unknown distribution charts |
| `research/src/experiments/cross_validation/visualize.py` | Cross-validation fold-specific visualizations |
| `research/src/analysis/retrieval_pipeline.py` | Retrieval pipeline comparison generation |

### Data Sources

| Data File | Used By |
|-----------|---------|
| `results/retrieval_pipeline_comparison.csv` | extractor_comparison, confusion_best/worst, retrieval_family |
| `results/cross_validation/cv_summary_table.csv` | cv_heatmap_*, cv_model_comparison |
| `results/cross_validation/cv_results.csv` | fold_variance_new |
| `results/threshold/log/all_experiments.csv` | threshold_top_bar |
| `results/threshold/threshold_summary.json` | threshold summary |
| `results/segmentation_comparison/comparison.csv` | segmentation_comparison |

### Running Chart Generation

```bash
# From monorepo root — generate all charts
uv --directory research run python docs/graduation_report/code/chart_experiment_results.py

# Or run individual scripts
uv --directory research run python -m src.analysis.final_charts
uv --directory research run python -m src.analysis.graduation_report_assets
```

Charts are saved to both `docs/graduation_report/latex/figures/` (LaTeX) and `graduation_report/report/figures/` (HTML report).

## LaTeX Report Structure

```
main.tex
├── Cover.tex                    # Title page
├── Chapter/0_2_Acknowledgment.tex
├── Chapter/0_3_Abstract.tex
├── Chapter/1_Introduction.tex   # Motivation, problem statement
├── Chapter/2_Literature_Review.tex  # Methodology + Experiment Results
├── Chapter/3_Methodology.tex    # Web application design
├── Chapter/4_Implementation.tex # Agentic engineering + E2E testing
├── Chapter/5_Evaluation.tex     # Summary + future work
├── Chapter/Appendix_B.tex       # Use case descriptions
```

### Chapter Content Rules

- **Chapter 2**: All experiment methodology AND results live here. This includes segmentation, feature extraction, fine-tuning, retrieval, cross-validation, and threshold experiments. Discussion and findings at the end.
- **Chapter 3**: Web application design — architecture, component design, API design, frontend routes.
- **Chapter 4**: Agentic engineering workflow (Autolab system), E2E browser testing, CI/CD, and a single summary table referencing Chapter 2 results. No raw experiment data — only the summary table and config alignment verification.
- **Chapter 5**: Summary of contributions, future work directions.

## Chart Visualization Style Rules

### Python (matplotlib/seaborn)

```python
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
})

# Dual-save pattern — always save to BOTH destinations
def save(name, fig):
    for out in [LATEX_DIR/name, REPORT_DIR/name]:
        fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
```

**Style rules:**
- Serif font, 8pt base
- White background, no gridlines unless comparing two groups
- Color palette: `#1f77b4` (blue), `#ff7f0e` (orange), `#2ca02c` (green) — consistent across all charts
- Fine-tuned DL = blue, Pretrained DL = orange, Traditional = green
- Bar charts: show value labels on bars, edgecolor=white
- Heatmaps: `YlOrRd` colormap, show text values in cells (white text on dark cells, black on light)
- Confusion matrices: `Blues` colormap, row-normalized with count and fraction per cell
- Save at 200 DPI, tight bounding box
- Always `plt.close(fig)` after save to prevent memory leaks

### Mermaid Diagrams

```bash
# Render mermaid .mmd file to PNG
uvx --from mermaid-cli mmdc -i input.mmd -o output.png
```

Mermaid diagrams are rendered separately and committed as PNGs. Source `.mmd` files should live alongside the output.

### New Figure Integration

1. Generate the PNG in `docs/graduation_report/latex/figures/`
2. Reference in `.tex` chapter file:
   ```latex
   \begin{figure}[ht]
   \centering
   \includegraphics[width=\textwidth]{figure_name.png}
   \caption{Description.}
   \label{fig:figure_name}
   \end{figure}
   ```
3. Reference in text: `Figure~\ref{fig:figure_name}`
4. No `figures/` prefix in `\includegraphics` — `\graphicspath{{figures/}}` handles it

## Compilation

```bash
# From the latex directory
cd docs/graduation_report/latex

# Clean build
rm -f main.aux main.lof main.log main.lot main.out main.toc main.run.xml main-blx.bib

# Compile (bibtex for references, 2 pdflatex passes for TOC resolution)
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

### Warning Suppression Strategy

- **Citation warnings** (`undefined`): Add missing entries to `reference.bib`. If a citation is intentionally using a working title or preprint, add it with a `note` field.
- **Overfull hbox**: Adjust paragraph wording, add `\sloppy` or `\emergencystretch=1em` (already configured).
- **Font warnings**: Ensure all referenced fonts are installed (e.g., Times via `\usepackage{times}`).
- The preamble already suppresses `\PackageWarning` for `biblatex` backend warnings. Do NOT suppress citation `undefined` warnings — fix them instead.

## Update Workflow

### Adding a New Experiment Result

1. Run the experiment and save results to `results/<experiment>/`
2. Run chart generation:
   ```bash
   uv --directory research run python docs/graduation_report/code/chart_experiment_results.py
   ```
3. Verify new charts in `docs/graduation_report/latex/figures/`
4. Update the relevant subsection in `Chapter/2_Literature_Review.tex`
5. Update the summary table in `Chapter/4_Implementation.tex` (Table 4.1)
6. Recompile and verify zero warnings:
   ```bash
   cd docs/graduation_report/latex && pdflatex main.tex && bibtex main && pdflatex main.tex && pdflatex main.tex
   ```

### Adding a New Chart Type

1. Write generation code in `docs/graduation_report/code/` — one file per chart family
2. Follow the dual-save pattern (LATEX_DIR + REPORT_DIR)
3. Use the canonical color palette and style rules above
4. Integrate into the chart update script
5. Document the data source here in the table above

## Current Figures Inventory

Generated by `code/chart_experiment_results.py`:
- `extractor_comparison.png` — Feature extractor column chart
- `cv_heatmap_*.png` — Cross-validation heatmaps (6 total)
- `confusion_best_*.png` / `confusion_worst_*.png` — Confusion matrices (5 total)
- `retrieval_family_comparison.png` — Top retrieval by extractor family
- `threshold_top_bar.png` — Top threshold strategies bar chart

Generated by `research/src/analysis/final_charts.py`:
- `segmentation_comparison.png` — YOLO vs K-means
- `training_curves_folds.png` — Per-fold training curves
- `cv_fold_configs.png` — Best CV configurations bar chart
- `fold_variance_new.png` — Per-fold accuracy distribution

External/copied assets (not auto-generated):
- `query_flow.png` — Pipeline diagram (manual)
- `pipeline_montage.jpg` — Dish-to-crop montage (manual)
- `kmeans_vs_yolo_comparison.png` — Segmentation visual comparison (manual)
- `e2e_*.png` — Browser test screenshots (captured via agent-browser)
- `ch03_*.png` — System architecture diagrams (mermaid rendered)
