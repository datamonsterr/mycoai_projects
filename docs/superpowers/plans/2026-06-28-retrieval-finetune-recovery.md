# Retrieval Fine-Tune Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix fine-tune, feature extraction, retrieval, and reporting workflow so finetuned extractors are retrained on the strain-holdout split, extracted on Vast.ai, re-evaluated locally through canonical Qdrant retrieval artifacts, and iterated until finetuned models outperform pretrained baselines on the 6-testset evaluation.

**Architecture:** Keep training and extraction remote-only, but keep bug diagnosis, Qdrant upload, retrieval evaluation, and report generation local. Patch the shared code paths that define strain/species mapping, finetuned weight loading, augmentation/training policy, retrieval artifact naming, and local analytics outputs so every loop uses the same canonical pipeline and produces comparable evidence.

**Tech Stack:** Python 3.13, PyTorch, torchvision, pandas, Qdrant, matplotlib/seaborn, uv, Vast.ai CLI, git.

---

## File Map

- Modify: `research/src/experiments/finetune_dl/train_strain_holdout.py`
- Modify: `research/src/experiments/finetune_dl/train_models.py`
- Modify: `research/src/experiments/feature_extraction/feature_extractors.py`
- Modify: `research/src/experiments/feature_extraction/generate_features.py`
- Modify: `research/src/experiments/retrieval/run.py`
- Modify: `research/src/utils/upload_qdrant.py`
- Modify: `graduation_report/code/chart_experiment_results.py`
- Modify: `graduation_report/Chapter/2_Literature_Review.tex`
- Modify: `docs/graduation_report/README.md`
- Create: `graduation_report/code/chart_finetune_retrieval_recovery.py`
- Create: `graduation_report/code/augmentation_preview_recovery.py`
- Create: `graduation_report/figures/finetune_retrieval_recovery_flow.mmd`
- Create: `graduation_report/figures/finetune_retrieval_recovery_flow.png`
- Create: `results/retrieval_<datetime>/...` via pipeline
- Create: `results/augmentation_preview/...` via pipeline

### Task 1: Audit split correctness and finetuned weight loading

**Files:**
- Modify: `research/src/experiments/finetune_dl/train_strain_holdout.py`
- Modify: `research/src/experiments/feature_extraction/feature_extractors.py`
- Test: local ad-hoc `uv --directory research run python ...`

- [ ] **Step 1: Inspect current split and loader behavior against dataset layout**

Run:
```bash
uv --directory research run python - <<'PY'
from pathlib import Path
from src.config import ORIGINAL_PREPARED_DATASET_DIR, STRAIN_SPECIES_MAPPING_PATH
from src.experiments.finetune_dl.train_strain_holdout import load_split_mapping, strain_to_species_from_original_prepared, collect_segment_paths

test_strains, csv_map = load_split_mapping(STRAIN_SPECIES_MAPPING_PATH)
dir_map = strain_to_species_from_original_prepared(ORIGINAL_PREPARED_DATASET_DIR)
path_map = collect_segment_paths(ORIGINAL_PREPARED_DATASET_DIR, "yolo")
missing_csv = sorted([s for s in test_strains if s not in dir_map])
missing_segments = sorted([s for s in csv_map if s not in path_map])
print({
    "test_strain_count": len(test_strains),
    "csv_strain_count": len(csv_map),
    "dir_strain_count": len(dir_map),
    "segment_strain_count": len(path_map),
    "missing_csv_in_dirs": missing_csv[:20],
    "missing_csv_in_segments": missing_segments[:20],
})
PY
```
Expected: real counts plus any mismatched strain names to fix in code.

- [ ] **Step 2: Patch split normalization and mismatch reporting in holdout trainer**

Implement in `research/src/experiments/finetune_dl/train_strain_holdout.py`:
```python
def normalize_strain_name(value: str) -> str:
    cleaned = " ".join(str(value).strip().replace("_", " ").split())
    return cleaned.upper()


def normalize_species_name(value: str) -> str:
    return " ".join(str(value).strip().replace("_", " ").split()).lower()
```
Use these helpers when reading CSV rows, parsing directory names, and matching `test_strains` / `strain_to_species`. Raise a `ValueError` with exact missing strains if normalized CSV names still do not exist in `Dataset/original_prepared`.

- [ ] **Step 3: Patch finetuned extractor loaders to prove non-ImageNet weights actually load**

Implement in `research/src/experiments/feature_extraction/feature_extractors.py`:
```python
def _unwrap_state_dict(checkpoint: Any) -> dict[str, Any]:
    if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
        return checkpoint["state_dict"]
    return checkpoint
```
Use this helper in `ResNet50Extractor._build_model`, `MobileNetV2Extractor._build_model`, and `EfficientNetB1Extractor._build_model`. Strip optional prefixes like `module.` before `load_state_dict`, and print how many backbone keys loaded.

- [ ] **Step 4: Run focused verification for split and weight loader**

Run:
```bash
uv --directory research run python - <<'PY'
from src.experiments.finetune_dl.train_strain_holdout import build_dataloaders
from src.experiments.feature_extraction.feature_extractors import ResNet50FinetunedExtractor, MobileNetV2FinetunedExtractor, EfficientNetB1FinetunedExtractor
from src.config import ORIGINAL_PREPARED_DATASET_DIR, STRAIN_SPECIES_MAPPING_PATH

train_loader, val_loader, encoder, counts = build_dataloaders(
    dataset_root=ORIGINAL_PREPARED_DATASET_DIR,
    mapping_path=STRAIN_SPECIES_MAPPING_PATH,
    segment_method="yolo",
    image_size=224,
    batch_size=4,
)
print(counts)
for cls in (ResNet50FinetunedExtractor, MobileNetV2FinetunedExtractor, EfficientNetB1FinetunedExtractor):
    try:
        model = cls()
        print(cls.__name__, model.name)
    except Exception as exc:
        print(cls.__name__, "FAILED", exc)
        raise
PY
```
Expected: non-empty train/val counts and all three finetuned extractors instantiate successfully.

- [ ] **Step 5: Commit split/loader fix**

Run:
```bash
git add research/src/experiments/finetune_dl/train_strain_holdout.py research/src/experiments/feature_extraction/feature_extractors.py
git commit -m "fix(research): normalize holdout split and finetuned loaders"
```
Expected: commit succeeds with detailed message.

### Task 2: Add augmentation policy, preview assets, and stronger training controls

**Files:**
- Modify: `research/src/experiments/finetune_dl/train_strain_holdout.py`
- Modify: `research/src/experiments/finetune_dl/train_models.py`
- Create: `graduation_report/code/augmentation_preview_recovery.py`
- Test: local preview/training smoke commands

- [ ] **Step 1: Extend training augmentations to include random cuts + brightness/contrast**

Implement in `research/src/experiments/finetune_dl/train_strain_holdout.py` training transform:
```python
ops.extend([
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.RandomResizedCrop((image_size, image_size), scale=(0.75, 1.0), ratio=(0.9, 1.1)),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
])
```
Apply same policy to legacy `train_models.py` or redirect that module to same shared transform builder so old path cannot drift.

- [ ] **Step 2: Save best-validation metadata needed for later comparison**

Update `run_strain_holdout_finetuning` summary payload in `research/src/experiments/finetune_dl/train_strain_holdout.py` to record epoch-wise `history`, `best_val_accuracy`, and normalized split audit fields such as `missing_csv_strains`, `resolved_test_strains`, and augmentation config.

- [ ] **Step 3: Create augmentation preview script for report assets**

Create `graduation_report/code/augmentation_preview_recovery.py` with code that loads one or more sample YOLO segment images, applies baseline + augmented transforms deterministically, and saves grid PNGs to `graduation_report/figures/` and mirrored report output.

Core code:
```python
fig, axes = plt.subplots(2, 3, figsize=(7.2, 4.8))
axes[0, 0].imshow(original)
axes[0, 0].set_title("Original")
for idx, aug_img in enumerate(samples, start=1):
    axes.flat[idx].imshow(aug_img)
    axes.flat[idx].set_title(titles[idx - 1])
```
Include views for crop, brightness+, contrast+, combined, and rotation.

- [ ] **Step 4: Run preview and one-epoch training smoke test**

Run:
```bash
uv --directory research run python graduation_report/code/augmentation_preview_recovery.py
uv --directory research run python -m src.experiments.finetune_dl.train_strain_holdout --model-name ResNet50 --segment-method yolo --epochs 1 --batch-size 4 --learning-rate 1e-4
```
Expected: preview figure saved and smoke training writes summary/weights without crash.

- [ ] **Step 5: Commit augmentation/training controls**

Run:
```bash
git add research/src/experiments/finetune_dl/train_strain_holdout.py research/src/experiments/finetune_dl/train_models.py graduation_report/code/augmentation_preview_recovery.py
git commit -m "feat(research): add holdout augmentation preview and training policy"
```
Expected: commit succeeds.

### Task 3: Canonicalize remote extraction outputs and local retrieval artifact naming

**Files:**
- Modify: `research/src/experiments/feature_extraction/generate_features.py`
- Modify: `research/src/experiments/retrieval/run.py`
- Modify: `research/src/utils/upload_qdrant.py`
- Test: local feature JSON generation + retrieval dry run

- [ ] **Step 1: Make feature generation controllable by extractor set and output JSON path**

Update `generate_features()` in `research/src/experiments/feature_extraction/generate_features.py` to accept explicit extractor names and output path from CLI/caller. Ensure all pretrained, finetuned, and traditional extractors can be selected without hidden defaults.

- [ ] **Step 2: Enforce canonical retrieval result folder format**

Update `research/src/experiments/retrieval/run.py` comprehensive/local evaluation output naming so retrieval directories are created under:
```python
results_root = RESULTS_DIR / f"retrieval_{timestamp}"
run_dir = results_root / f"{feature_extractor.name}_{k}_{strategy}_{media_label}_{segmentation_label}"
```
Use `weighted`, `E1`, and `k=7` labels exactly as user requested.

- [ ] **Step 3: Ensure local evaluation emits all requested analytics artifacts**

Extend retrieval pipeline to always save:
```python
confusion_matrix.png
prediction_report_<timestamp>.txt
evaluation_results.json
<run_dir_name>.csv
visualizations/correct/*
visualizations/incorrect/*
```
Add per-run analytics summary JSON/CSV if missing, not only human-readable text.

- [ ] **Step 4: Harden Qdrant upload mapping for CSV-derived species names**

Fix `_load_strain_species_mapping()` in `research/src/utils/upload_qdrant.py` so CSV parsing always returns mapping instead of returning `{}` for JSON suffix branches. Normalize strain names before lookup to keep local upload aligned with training split.

- [ ] **Step 5: Run local dry-run verification**

Run:
```bash
uv --directory research run python - <<'PY'
from pathlib import Path
from src.experiments.feature_extraction.generate_features import generate_features
out = Path('/tmp/opencode/retrieval_smoke_features.json')
generate_features(output_path=out, image_dir=None, segment_method='yolo')
print(out.exists(), out.stat().st_size)
PY
```
Then run one local retrieval command against current Qdrant collection using weighted/E1/K7 and confirm folder naming matches `<feature>_7_weighted_E1_<segmentation>`.

- [ ] **Step 6: Commit retrieval/Qdrant canonicalization**

Run:
```bash
git add research/src/experiments/feature_extraction/generate_features.py research/src/experiments/retrieval/run.py research/src/utils/upload_qdrant.py
git commit -m "fix(retrieval): canonicalize artifacts and qdrant mapping"
```
Expected: commit succeeds.

### Task 4: Run Vast.ai retraining and extraction loop

**Files:**
- Modify if needed after failures: `research/src/experiments/finetune_dl/*`, `research/src/experiments/feature_extraction/*`
- Use: `research/resources/vast.md`, `rules/vast.md`
- Artifact roots: `/workspace/drive/results/<timestamp>_finetune-retrieval-recovery/`, `/workspace/drive/weights/<timestamp>_finetune-retrieval-recovery/`

- [ ] **Step 1: Verify local status before remote run**

Run:
```bash
vastai show instance 42862866
uv --directory research run python -m src.experiments.finetune_dl.train_strain_holdout --model-name ResNet50 --segment-method yolo --epochs 1 --batch-size 4
```
Expected: instance reachable and local smoke still green before sync.

- [ ] **Step 2: Run remote training for all target deep models**

Run on Vast.ai via canonical runner path:
```bash
uv --directory research run python -m src.experiments.finetune_dl.train_strain_holdout --model-name ResNet50 --segment-method yolo --epochs 12 --batch-size 16 --learning-rate 1e-4 --patience 10
uv --directory research run python -m src.experiments.finetune_dl.train_strain_holdout --model-name MobileNetV2 --segment-method yolo --epochs 12 --batch-size 16 --learning-rate 1e-4 --patience 10
uv --directory research run python -m src.experiments.finetune_dl.train_strain_holdout --model-name EfficientNetB1 --segment-method yolo --epochs 12 --batch-size 16 --learning-rate 1e-4 --patience 10
```
Expected: fresh `_finetuned.pth`, classifier checkpoints, and summary JSONs under `weights/yolo_finetuned/`.

- [ ] **Step 3: Run remote feature extraction JSON generation**

Run on Vast.ai:
```bash
uv --directory research run python - <<'PY'
from pathlib import Path
from src.experiments.feature_extraction.generate_features import generate_features
from src.config import RESULTS_DIR
out = RESULTS_DIR / 'remote_features_yolo_recovery.json'
generate_features(output_path=out, image_dir=None, segment_method='yolo')
print(out)
PY
```
Expected: one JSON containing vectors for pretrained, finetuned, and traditional extractors.

- [ ] **Step 4: Stage artifacts to Drive and download locally**

Copy remote outputs to:
```text
/workspace/drive/results/<YYYYMMDD-HHMMSS>_finetune-retrieval-recovery/
/workspace/drive/weights/<YYYYMMDD-HHMMSS>_finetune-retrieval-recovery/
```
Then sync those staged folders back to local `results/` and `weights/`.

- [ ] **Step 5: If remote training fails or finetuned is still worse, patch locally and create new fix commit**

For every loop failure, repeat:
```bash
git status
git diff
# fix code
# rerun smoke tests
git add <files>
git commit -m "fix(finetune): <detailed cause-specific message>"
```
Expected: every fix preserved as actual commit before next remote rerun.

### Task 5: Run local Qdrant upload + canonical retrieval comparison loop

**Files:**
- Modify if needed after evidence: `research/src/experiments/retrieval/run.py`, `research/src/utils/upload_qdrant.py`, extractor/training code
- Artifact roots: `results/retrieval_<datetime>/...`

- [ ] **Step 1: Clear and repopulate local research collection from recovered feature JSON**

Run:
```bash
uv --directory research run python -m src.utils.upload_qdrant --features-json results/remote_features_yolo_recovery.json --collection qdrant-research --batch-size 100
```
Expected: collection deleted/recreated and point count matches JSON record count.

- [ ] **Step 2: Run canonical local retrieval for all extractor families**

Run local retrieval using only `weighted`, `E1`, `k=7` and emit one run folder per extractor:
```bash
uv --directory research run python -m src.experiments.retrieval.run comprehensive --identifier local_recovery --extractors resnet50 resnet50_finetuned mobilenetv2 mobilenetv2_finetuned efficientnetb1 efficientnetb1_finetuned hog gabor colorhistogram colorhistogramhs --env_strategies E1 --agg_strategies weighted --k 7
```
Expected: results under `results/retrieval_<datetime>/resnet50_7_weighted_E1_yolo/` etc.

- [ ] **Step 3: Compare finetuned vs pretrained on 6-testset evidence**

Use generated JSON/CSV reports to compute paired comparison by family:
```python
families = [
    ("resnet50_finetuned", "resnet50"),
    ("mobilenetv2_finetuned", "mobilenetv2"),
    ("efficientnetb1_finetuned", "efficientnetb1"),
]
```
Require finetuned accuracy > pretrained accuracy for each family, using local canonical retrieval outputs only.

- [ ] **Step 4: If any finetuned model still loses, loop back to Task 1 or Task 2 based on evidence**

Decision rule:
```text
weight-load mismatch -> Task 1
split / label mismatch -> Task 1
underfit or unstable val accuracy -> Task 2 / Task 4 retrain params
artifact / retrieval mismatch -> Task 3 / Task 5
```
Do not stop until all three finetuned models beat their pretrained baselines or a hard blocker requires user input.

- [ ] **Step 5: Run full local verification before final reporting**

Run:
```bash
uv --directory research run python -m ruff check src/experiments/ src/utils/upload_qdrant.py
uv --directory research run pytest tests/ -q
```
If repo has narrower required checks for changed paths, run them too. Only claim success after fresh green output.

### Task 6: Update graduation report figures, analytics, and narrative

**Files:**
- Create: `graduation_report/code/chart_finetune_retrieval_recovery.py`
- Modify: `graduation_report/code/chart_experiment_results.py`
- Modify: `graduation_report/Chapter/2_Literature_Review.tex`
- Modify: `docs/graduation_report/README.md`
- Create: `graduation_report/figures/finetune_retrieval_recovery_flow.mmd`
- Create: `graduation_report/figures/finetune_retrieval_recovery_flow.png`

- [ ] **Step 1: Create recovery chart script from final local retrieval outputs**

Generate figures for:
```text
- finetuned vs pretrained grouped bar chart
- per-family delta chart
- augmentation preview inclusion helper
- confusion matrix copies for best final runs
- training/validation accuracy history overlays
```
Save to both LaTeX and report output folders.

- [ ] **Step 2: Add Mermaid flow diagram for train/extract/transfer/retrieve loop**

Create `finetune_retrieval_recovery_flow.mmd` describing:
```text
Local bug fix -> Vast.ai retrain -> Vast.ai feature extraction -> Drive staging -> Local download -> Qdrant upload -> Local weighted/E1/K7 retrieval -> Compare FT vs PT -> Loop or report
```
Render PNG and commit both source + output.

- [ ] **Step 3: Update Chapter 2 narrative with final methodology and findings**

Add concise section covering:
```text
- strain_to_specy.csv split validation against Dataset/original_prepared
- augmentation design (random cuts, brightness, contrast)
- best-validation checkpoint selection
- Vast.ai remote-only training/extraction
- local Qdrant evaluation and 6-testset comparison
- final evidence that finetuned models outperform pretrained baselines
```
Reference new figures by `\label{}` and update surrounding analysis text.

- [ ] **Step 4: Update report README data-source notes**

Document new chart script, retrieval folder naming, and recovery workflow in `docs/graduation_report/README.md`.

- [ ] **Step 5: Compile report and verify output**

Run:
```bash
python graduation_report/code/chart_finetune_retrieval_recovery.py
python graduation_report/code/augmentation_preview_recovery.py
```
Then compile:
```bash
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```
from `graduation_report/`.
Expected: PDF builds and new figures appear.

- [ ] **Step 6: Commit report updates**

Run:
```bash
git add graduation_report/code graduation_report/Chapter/2_Literature_Review.tex docs/graduation_report/README.md graduation_report/figures/finetune_retrieval_recovery_flow.mmd graduation_report/figures/finetune_retrieval_recovery_flow.png
git commit -m "docs(graduation): add finetune retrieval recovery analysis"
```
Expected: final report commit succeeds.

## Self-Review

- Spec coverage: plan covers local bug audit, strain split validation, augmentation preview, Vast-only retrain/extract, local Qdrant retrieval, repeated comparison loop, actual commits, and report updates.
- Placeholder scan: no TBD/TODO placeholders remain; commands and file paths are explicit.
- Type consistency: extractor names, segment method `yolo`, aggregation `weighted`, media `E1`, and `k=7` stay consistent across tasks.
