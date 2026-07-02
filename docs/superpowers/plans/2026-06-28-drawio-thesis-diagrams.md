# Draw.io Thesis Diagram Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vendor `drawio-ai-kit` into this repo, wire reproducible local diagram generation for graduation thesis assets, and replace selected Mermaid/manual PNG architecture diagrams with draw.io-sourced exports while keeping sequence and use-case diagrams unchanged.

**Architecture:** Keep `drawio-ai-kit` as a vendored tool under `tools/` so thesis assets remain reproducible from repo state. Store source `.drawio` and/or generator scripts beside thesis assets under `graduation_report/figures/`, export PNGs consumed by LaTeX, and document exact regeneration commands in the graduation report README.

**Tech Stack:** Node 18+, npm, draw.io desktop CLI, vendored drawio-ai-kit, LaTeX, existing thesis chapter files

---

### Task 1: Vendor drawio-ai-kit and inspect its local workflow

**Files:**
- Create: `tools/drawio-ai-kit/`
- Modify: `docs/graduation_report/README.md`

- [ ] **Step 1: Clone repository into vendored tools path**

```bash
git clone https://github.com/sparklabx/drawio-ai-kit.git /home/dat/dev/mycoai_projects/tools/drawio-ai-kit
```

- [ ] **Step 2: Install Node dependencies for vendored tool**

Run: `npm install`
Workdir: `/home/dat/dev/mycoai_projects/tools/drawio-ai-kit`
Expected: install completes without lifecycle-hook surprises and creates `node_modules/`

- [ ] **Step 3: Verify bundled CLI and tests work**

Run: `node src/cli.mjs principles && npm test`
Workdir: `/home/dat/dev/mycoai_projects/tools/drawio-ai-kit`
Expected: principles text prints and Node tests pass

- [ ] **Step 4: Document thesis-local usage**

Add README section covering vendored path, install command, draw.io desktop requirement, and export workflow for thesis figures.

### Task 2: Inventory thesis diagrams and define migration targets

**Files:**
- Modify: `docs/graduation_report/README.md`
- Inspect: `graduation_report/Chapter/2_Literature_Review.tex`
- Inspect: `graduation_report/Chapter/3_Methodology.tex`

- [ ] **Step 1: Confirm exact thesis assets to migrate**

Targets:
- `graduation_report/figures/ch03_architecture.png`
- `graduation_report/figures/ch03_erd.png`
- `graduation_report/figures/ch02_research_pipeline.png`
- `graduation_report/figures/threshold_pipeline_diagram.png`

- [ ] **Step 2: Preserve exclusions explicitly**

Keep unchanged:
- `ch03_usecase_diagram.png`
- sequence diagrams: `ch03_auth_sequence.png`, `ch03_srs_retrieve_sequence.png`, `ch03_srs_index_sequence.png`, `ch03_srs_feedback_sequence.png`

- [ ] **Step 3: Update README migration rules**

Document that system design, ERD, methodology, and algorithm diagrams use draw.io sources; sequence diagrams remain Mermaid; use-case diagram remains current source.

### Task 3: Add source asset structure for draw.io thesis diagrams

**Files:**
- Create: `graduation_report/figures/src/`
- Create: `graduation_report/figures/src/ch03_architecture.drawio`
- Create: `graduation_report/figures/src/ch03_erd.drawio`
- Create: `graduation_report/figures/src/ch02_research_pipeline.drawio`
- Create: `graduation_report/figures/src/threshold_pipeline_diagram.drawio`
- Create: `graduation_report/code/export_drawio_diagrams.py` or `graduation_report/code/export_drawio_diagrams.sh`

- [ ] **Step 1: Create source directory for versioned draw.io assets**

Use `graduation_report/figures/src/` so thesis consumers can track editable diagram sources separately from exported PNGs.

- [ ] **Step 2: Add source diagrams with thesis-aligned names**

Source and export naming must match existing LaTeX references so chapter files need minimal or zero edits.

- [ ] **Step 3: Add one export entrypoint**

Script must export each `.drawio` source to `graduation_report/figures/*.png` using draw.io CLI, for example:

```bash
DRAWIO_CLI=${DRAWIO_CLI:-drawio}
"$DRAWIO_CLI" --export --format png --output ch03_architecture.png ch03_architecture.drawio
```

### Task 4: Create architecture and methodology diagrams with drawio-ai-kit workflow

**Files:**
- Create/Modify: `graduation_report/figures/src/ch03_architecture.drawio`
- Create/Modify: `graduation_report/figures/src/ch02_research_pipeline.drawio`
- Create/Modify: `graduation_report/figures/src/threshold_pipeline_diagram.drawio`
- Optional Create: `graduation_report/code/drawio_generators/*.mjs`

- [ ] **Step 1: Build system architecture diagram**

Contents must match `graduation_report/Chapter/3_Methodology.tex:79-85`: React SPA frontend, FastAPI backend, PostgreSQL, Qdrant, Redis, Celery worker, containerized boundaries.

- [ ] **Step 2: Build research methodology pipeline diagram**

Translate `graduation_report/content/methodology_pipeline.md:1-54` from Mermaid flow to draw.io with four stages and branching paths.

- [ ] **Step 3: Build threshold/algorithm pipeline diagram**

Preserve Chapter 2 semantics around threshold known-vs-unknown decision flow, but render from draw.io source instead of previous manual/Mermaid asset.

- [ ] **Step 4: Export PNGs and visually inspect layout**

Run export script and verify no clipped labels, crossed connectors, or illegible stage titles.

### Task 5: Create ERD diagram from backend schema

**Files:**
- Create/Modify: `graduation_report/figures/src/ch03_erd.drawio`
- Inspect: backend model files for actual entities/relations

- [ ] **Step 1: Read backend schema source before drawing**

Use backend models, not thesis prose, as source of truth for tables and relations.

- [ ] **Step 2: Build thesis-level ERD**

Include major entities only: users, species, media, strains, images, segments, feedback, audit log, jobs/model-index state where relevant. Keep readable on thesis page.

- [ ] **Step 3: Export PNG and verify readability**

Run export script and ensure table text remains legible at thesis print scale.

### Task 6: Integrate and verify thesis build

**Files:**
- Modify: `docs/graduation_report/README.md`
- Possibly Modify: chapter `.tex` files only if filenames or captions change

- [ ] **Step 1: Keep LaTeX include paths stable**

Prefer same output PNG filenames so references in `Chapter/2_Literature_Review.tex` and `Chapter/3_Methodology.tex` remain unchanged.

- [ ] **Step 2: Rebuild thesis PDF**

Run LaTeX compile from `graduation_report/` until references settle.
Expected: PDF builds and new draw.io-generated figures appear in correct chapters.

- [ ] **Step 3: Run local validation commands**

Run:
- `npm test` in `tools/drawio-ai-kit`
- thesis export script for draw.io assets
- LaTeX compile for `graduation_report/main.tex`

- [ ] **Step 4: Final README note**

Document exact regenerate sequence for future edits.
