# Retrieval Research Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild research pipeline so closed-set, open-set, segmentation, feature extraction, thresholding, reporting, and product handoff all follow leakage-safe strain-level evaluation with explicit user confirmation gates.

**Architecture:** Keep `research/` as source of truth for experiment execution, artifacts, and reports. Add a new leakage-safe evaluation path that always preprocesses, segments, and extracts query features from held-out images instead of querying by in-database test IDs. Separate experiment phases into: dataset audit, segmentation validation, retrieval benchmark, open-set thresholding, report generation, then backend/frontend adoption.

**Tech Stack:** Python 3.13, uv, Qdrant, pandas, PyTorch/torchvision, OpenCV, PIL, matplotlib/seaborn, Docker, Vast.ai, pnpm, FastAPI, React 19 + Vite.

---

## File map

- Modify: `research/docs/TERMINOLOGY.md` — align split language, Media terminology, experiment terms.
- Modify: `research/src/utils/qdrant_query.py` — enforce strain exclusion for benchmark helpers and add query-by-file safe path.
- Modify: `research/src/experiments/retrieval/run.py` — add leakage-safe query pipeline, more aggregation/media options, per-case CSV/report/evidence outputs.
- Modify: `research/src/experiments/cross_validation/run.py` — expand CV matrix, output structured artifacts, add confirmation manifests.
- Modify: `research/src/experiments/finetune_dl/train_models.py` — remove global `Test` leakage assumption, support fold-specific mapping and strict train/val split.
- Modify: `research/src/utils/generate_cv_fold_mappings.py` — generate fold maps consumed by finetune and retrieval.
- Modify: `research/src/analysis/visualization/visualize_prediction.py` — expose clearer evidence overlays and verification instructions.
- Create: `research/src/experiments/research_audit/` — dataset/Qdrant/weights/report audit entrypoint.
- Create: `research/src/experiments/research_plan/` — experiment order manifest and status ledger.
- Create: `docs/RESEARCH.md` — cumulative research progress log and comparison table.
- Modify: `docs/graduation_report/content/02-retrieval-model.md` — replace stale claims with confirmed experiment-backed content.
- Modify later: `backend/` and `frontend/` integration files after best experiment confirmed.

### Task 1: Freeze research protocol and terminology

**Files:**
- Modify: `research/docs/TERMINOLOGY.md`
- Create: `docs/RESEARCH.md`
- Create: `research/docs/RESEARCH_PROTOCOL.md`

- [ ] Record confirmed protocol: leave-one-strain-out closed-set, open-set split into unseen-strain and unseen-species tracks, missing/new Media uses available Media only, output includes ranking + threshold + evidence.
- [ ] Rename user-facing docs to prefer `Media`; keep `environment strategy` as internal experiment term only.
- [ ] Add explicit leakage bans: no test strain in finetune train set, no benchmark retrieval by in-database test ID, no stale historical metrics reused.
- [ ] Add confirmation gates section: segmentation visuals, evidence visuals, report conclusions, backend/frontend adoption each require user sign-off before next stage.

### Task 2: Audit current runtime state before implementation

**Files:**
- Create: `research/src/experiments/research_audit/run.py`
- Create: `research/src/experiments/research_audit/program.md`

- [ ] Inspect `Dataset/`, `weights/`, `results/`, `.qdrant_storage/`, Qdrant collections, prior reports, fold CSVs, and model files.
- [ ] Emit machine-readable audit outputs under `results/research_audit/`: `inventory.json`, `qdrant_collections.json`, `dataset_summary.csv`, `risk_flags.md`.
- [ ] Flag leakage risks and stale-claim risks from current codepaths.
- [ ] Ask user to review audit summary before any destructive refresh or long experiment.

### Task 3: Build strict fold assets for training and evaluation

**Files:**
- Modify: `research/src/utils/generate_cv_fold_mappings.py`
- Create: `research/src/utils/build_fold_manifests.py`
- Create: `research/tests/test_fold_manifests.py`

- [ ] Generate fold-specific CSV plus manifest JSON listing exact train/test strains, test query images, and allowed retrieval corpus.
- [ ] Add tests asserting no strain appears in both train and test sets for same fold.
- [ ] Add tests asserting every test image maps to exactly one held-out strain and one Media label.
- [ ] Save outputs under `Dataset/folds/` for downstream reproducibility.

### Task 4: Replace leakage-prone query path with preprocess→segment→extract→search path

**Files:**
- Modify: `research/src/utils/qdrant_query.py`
- Modify: `research/src/experiments/retrieval/run.py`
- Create: `research/tests/test_leakage_safe_query.py`

- [ ] Keep current ID-based query helper only for non-benchmark debugging.
- [ ] Add benchmark-safe helper that starts from file path / extracted query vectors and always passes `exclude_strain` for held-out strains.
- [ ] Add tests proving neighbor payloads never include held-out strain during evaluation.
- [ ] Add output field `retrieval_mode` = `db_id_debug` or `fresh_query_benchmark` to every result CSV/JSON.

### Task 5: Add segmentation-vs-full-image experiment track

**Files:**
- Create: `research/src/experiments/retrieval/full_image_baseline.py`
- Modify: `research/src/experiments/retrieval/program.md`
- Modify: `research/src/experiments/retrieval/run.py`

- [ ] Run baseline with full image only, no segmentation.
- [ ] Run segmented pipeline using same folds and same retrieval rules.
- [ ] Compare accuracy, rank quality, unknown detection, runtime, and explanation value.
- [ ] Produce side-by-side report artifacts so user can confirm whether segmentation is worth keeping.

### Task 6: Fix finetune training split and fold-specific weight export

**Files:**
- Modify: `research/src/experiments/finetune_dl/train_models.py`
- Create: `research/tests/test_finetune_split.py`
- Modify: `research/src/experiments/finetune_dl/program.md`

- [ ] Train per fold using fold manifest instead of single global `Test` column.
- [ ] Export weights and validation predictions per fold under `weights/folds/<fold>/` and `results/finetune_dl/<fold>/`.
- [ ] Add validation artifact CSV proving held-out strain predictions only use unseen training strains.
- [ ] Ask user to verify top correct/wrong validation visualizations before promoting a model family.

### Task 7: Expand retrieval benchmark matrix

**Files:**
- Modify: `research/src/experiments/cross_validation/run.py`
- Modify: `research/src/experiments/retrieval/run.py`
- Create: `research/src/analysis/retrieval/summarize_case_results.py`

- [ ] Evaluate k across configured grid.
- [ ] Evaluate Media strategies: same Media, all Media, single-Media subsets, leave-one-Media-out, available-Media-only query behavior.
- [ ] Evaluate aggregation: `weighted`, `uni`, `relative`, `freq_strength` and any retained variants.
- [ ] Write per-case CSV, per-strain CSV, summary CSV, confusion tables, rank@k tables, and visual evidence directories.

### Task 8: User confirmation gate — segmentation and evidence review

**Files:**
- Modify: `research/src/analysis/visualization/visualize_prediction.py`
- Create: `research/src/analysis/visualization/build_review_manifest.py`

- [ ] Generate curated review bundles: best/worst segmentation cases, correct/wrong retrieval cases, unknown accept/reject cases.
- [ ] Create `REVIEW.md` instructions per bundle: which folder to open, what to mark right/wrong, what decision is requested.
- [ ] Stop execution and ask user to confirm before proceeding to expensive follow-up experiments.

### Task 9: Rebuild open-set threshold experiments

**Files:**
- Modify: `research/src/experiments/threshold/retrieve_diverse.py`
- Modify: `research/src/experiments/threshold/program.md`
- Create: `research/src/experiments/threshold/run_openset_tracks.py`

- [ ] Separate unseen-strain and unseen-species tracks.
- [ ] Score both per-segment and aggregated-strain units if approved, otherwise chosen unit only.
- [ ] Optimize threshold under known-accuracy constraint; store chosen threshold plus rejected candidates.
- [ ] Generate per-case CSV, ROC/PR charts, threshold sweep charts, and evidence JSON/visuals.

### Task 10: Experiment ordering and report automation

**Files:**
- Create: `research/src/experiments/research_plan/run.py`
- Create: `research/src/experiments/research_plan/program.md`
- Modify: `docs/RESEARCH.md`

- [ ] Encode canonical order: audit → segmentation validation → full-image baseline → handcrafted retrieval benchmark → pretrained retrieval benchmark → finetuned retrieval benchmark → open-set thresholding → best-method product handoff.
- [ ] After each major phase, write report under `docs/` and append comparison row in `docs/RESEARCH.md`.
- [ ] Zip result folders for upload and write placeholder appendix URL fields for graduation report.

### Task 11: Graduation report update

**Files:**
- Modify: `docs/graduation_report/content/02-retrieval-model.md`
- Modify: `docs/graduation_report/content/main.md`

- [ ] Remove stale hardcoded metrics and unsupported claims.
- [ ] Insert only confirmed experiment-backed numbers, diagrams, and limitations.
- [ ] Add appendix placeholder URLs for zipped artifacts.

### Task 12: Backend/frontend adoption after best result confirmed

**Files:**
- Inspect then modify owner files in `backend/src/` and `frontend/src/`
- Add owner-repo tests per changed behavior

- [ ] Reimplement best confirmed retrieval/threshold behavior locally in backend.
- [ ] Surface ranking + unknown threshold + evidence in frontend.
- [ ] Run backend checks: `uv --directory backend run ruff check . && uv --directory backend run mypy . && uv --directory backend run pytest`
- [ ] Run frontend checks: `pnpm --dir frontend lint && pnpm --dir frontend typecheck && pnpm --dir frontend build`

## Immediate next execution block

1. Implement Task 1 + Task 2 only.
2. Present audit report + protocol diffs to user.
3. Wait for approval.
4. Implement Task 3–Task 5.
5. Stop for segmentation/full-image confirmation.

## Current verified risks

- `research/src/experiments/finetune_dl/train_models.py` uses one global `Test` column, not fold-safe training.
- `research/src/utils/qdrant_query.py` supports `exclude_strain`, but benchmark codepaths are not yet uniformly forced through fresh-query mode.
- `research/src/experiments/cross_validation/run.py` still benchmarks only E1/E2 and `weighted`/`uni`.
- `docs/graduation_report/content/02-retrieval-model.md` contains stale metrics that must be replaced after reruns.

## User confirmation gates

- Gate A: approve protocol + audit diff
- Gate B: approve segmentation quality review bundle
- Gate C: approve full-image vs segmented comparison
- Gate D: approve evidence visualizations and threshold behavior
- Gate E: approve backend/frontend adoption
- Gate F: approve commit/push for each completed experiment phase
