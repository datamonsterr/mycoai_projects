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

### Draw.io Thesis Diagrams

`drawio-ai-kit` is vendored at `tools/drawio-ai-kit/` so thesis diagram source and tooling stay pinned in repo state. Local use still requires `npm install` in the vendored path and a locally installed draw.io desktop CLI for PNG export.

Supported local prerequisites for thesis diagram work: Node 18+ and draw.io desktop available on `PATH` (or exposed through `DRAWIO_CLI`).

#### Install and Verify Vendored Tool

```bash
# From monorepo root
npm install --prefix tools/drawio-ai-kit
node tools/drawio-ai-kit/src/cli.mjs principles
npm test --prefix tools/drawio-ai-kit
```

Use upstream install flow inside this repo: install Node dependencies in the vendored path, then verify the CLI and test suite before editing thesis draw.io assets.

#### PNG Export: draw.io Desktop or Headless Chromium

Two export paths, tried in order by `code/export_drawio_diagrams.py`:

1. **draw.io desktop CLI** (preferred) — set `DRAWIO_CLI` or ensure `drawio` on `PATH`.
   ```bash
   export DRAWIO_CLI="/absolute/path/to/drawio"
   ```
2. **Headless Chromium** (fallback) — automatic when draw.io desktop not found. Requires `puppeteer` and `chromium` (`pacman -S puppeteer chromium`).
   ```bash
   npm install --prefix /tmp/puppeteer puppeteer
   NODE_PATH=/tmp/puppeteer/node_modules node code/export_drawio_headless.cjs
   ```

`drawio-ai-kit` can lint and generate XML without either export path.

#### Thesis Migration Targets and Exclusions

Draw.io-backed thesis diagram targets are fixed to current LaTeX includes so chapter files stay stable:

| Figure | Chapter source | Role | Planned editable source |
|--------|----------------|------|--------------------------|
| `ch03_architecture.png` | `latex/Chapter/3_Methodology.tex` | system architecture | `latex/figures/src/ch03_architecture.drawio` |
| `ch03_erd.png` | `latex/Chapter/3_Methodology.tex` | PostgreSQL ERD | `latex/figures/src/ch03_erd.dbml` (DBML) |
| `ch02_research_pipeline.png` | `latex/Chapter/2_Literature_Review.tex` | methodology pipeline | `latex/figures/src/ch02_research_pipeline.drawio` |
| `threshold_pipeline_diagram.png` | `latex/Chapter/2_Literature_Review.tex` | threshold algorithm flow | `latex/figures/src/threshold_pipeline_diagram.drawio` |

Migration exclusions are explicit:

- Keep `ch03_usecase_diagram.png` on current source path and workflow.
- Keep sequence diagrams Mermaid-sourced with neutral grey theme: `ch03_auth_sequence.png`, `ch03_srs_retrieve_sequence.png`, `ch03_srs_index_sequence.png`, `ch03_srs_feedback_sequence.png`.Sources live as `.mmd` files in `latex/figures/src/`, rendered via `code/render_mermaid_ink.py` (mermaid.ink API).
- Do not rename output PNGs without updating thesis chapter includes.

Migration rule for thesis diagrams: system design and algorithm diagrams use draw.io sources; ERD uses DBML (dbdiagram); sequence diagrams use Mermaid (neutral theme); use-case diagram remains current source.

#### Backend schema inventory for thesis ERD work

Backend schema source of truth for upcoming ERD work is `backend/src/backend/models/__init__.py` plus Alembic migrations in `backend/migrations/versions/`.

Major entities and relations confirmed during Task 2 review:

- `users` → `refresh_tokens`, `retrieval_jobs`, `feedback`, `training_jobs`, `audit_log`, `invite_tokens`
- `species` → `strains`, `images`
- `media` → `images`
- `strains` → `images`
- `images` → `segments`, `feedback`; also links back to `species`, `media`, `strains`
- `segments` → optional `qdrant_index_state`
- `retrieval_jobs` → `retrieval_results` → `retrieval_neighbors`
- `feedback` optionally links to `retrieval_results` and `images`, with submitter/reviewer both from `users`
- `training_jobs`, `audit_log`, `system_state`, and `invite_tokens` exist and may need thesis-level inclusion where model/index governance is discussed

Use backend schema as source of truth over thesis prose when building `ch03_erd.dbml`.

#### ERD Export (DBML → PNG)

```bash
npm install --prefix /tmp/dbml @softwaretechnik/dbml-renderer
bash docs/graduation_report/code/render_erd.sh
```

Requires `dbml-renderer` and `rsvg-convert` (librsvg). Source is `latex/figures/src/ch03_erd.dbml`.

#### Sequence Diagram Export (Mermaid → PNG, neutral theme)

```bash
python docs/graduation_report/code/render_mermaid_ink.py \
  docs/graduation_report/latex/figures/src/<name>.mmd \
  docs/graduation_report/latex/figures/<name>.png
```

Uses mermaid.ink API. Requires internet.

#### Thesis Export Workflow

1. Keep editable `.drawio` sources under `docs/graduation_report/latex/figures/src/`.
2. Export PNG outputs into `docs/graduation_report/latex/figures/` with filenames matching the LaTeX includes.
3. Choose export path (draw.io desktop or headless Chromium) — both write the same PNG set.
4. After export, rebuild LaTeX and verify updated figures render in thesis PDF.

Manual export fallback from repo root (draw.io desktop):

```bash
"${DRAWIO_CLI:-drawio}" --export --format png --output docs/graduation_report/latex/figures/<figure-name>.png docs/graduation_report/latex/figures/src/<figure-name>.drawio
```

Headless Chromium export fallback (no draw.io desktop needed):

```bash
NODE_PATH=/tmp/puppeteer/node_modules node docs/graduation_report/code/export_drawio_headless.cjs
```

Exact full regenerate sequence from repo root:

```bash
npm install --prefix tools/drawio-ai-kit
npm test --prefix tools/drawio-ai-kit
python docs/graduation_report/code/export_drawio_diagrams.py
cd docs/graduation_report/latex
pdflatex -interaction=nonstopmode main.tex
bibtex main
pdflatex -interaction=nonstopmode main.tex
pdflatex -interaction=nonstopmode main.tex
```

`export_drawio_diagrams.py` tries draw.io desktop first; if absent, falls back to headless Chromium (`export_drawio_headless.cjs`). If both unavailable, generators still run but PNG export is skipped (script exits non-zero).

Sequence diagrams remain Mermaid-driven unless a later task explicitly migrates them.

#### Thesis chapter references inspected for migration

- `latex/Chapter/2_Literature_Review.tex` uses `ch02_research_pipeline.png` for overall retrieval methodology and `threshold_pipeline_diagram.png` for threshold decision flow.
- `latex/Chapter/3_Methodology.tex` uses `ch03_architecture.png` for system architecture, `ch03_erd.png` for database design, `ch03_usecase_diagram.png` for use-case scope, and four `ch03_*sequence*.png` files for API workflow sequences.
- `docs/graduation_report/content/methodology_pipeline.md` currently holds Mermaid methodology source semantics that upcoming draw.io work should preserve.


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
