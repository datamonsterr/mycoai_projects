# Implementation Plan: Dataset Restructure and Derivation

**Branch**: `005-dataset-restructure` | **Date**: 2026-05-05 | **Spec**: [/home/dat/dev/mycoai/specs/005-dataset-restructure/spec.md](/home/dat/dev/mycoai/specs/005-dataset-restructure/spec.md)
**Input**: Feature specification from `/specs/005-dataset-restructure/spec.md`

## Summary

Restructure shared dataset assets for `repos/fungal-cv-qdrant` into one readable canonical hierarchy, replace split KMeans/YOLO reformat scripts with one preparation entrypoint, remove redundant flat `full_image` and `segmented_image` outputs, and update all retrieval, feature extraction, training, visualization, and sync touch points that currently assume old dataset paths.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: OpenCV, pandas, NumPy, ultralytics YOLO, qdrant-client, local filesystem dataset tooling  
**Package / Command Tooling**: `uv`/`uvx` for Python, shell commands for filesystem inspection, `gh` only if workflow checks are needed  
**Storage**: Filesystem-based dataset artifacts under monorepo `Dataset/`, metadata JSON/CSV sidecars, Qdrant feature upload inputs  
**Testing**: Repo Python checks plus targeted preparation/retrieval smoke tests via `uv --directory repos/fungal-cv-qdrant`; sync tool tests via `uv run pytest tools/tests/test_dataset_sync.py` if sync examples/contracts change  
**Target Platform**: Linux development workspace and remote Vast.ai Linux machines  
**Project Type**: Python experiment/data-preparation CLI plus shared dataset artifact pipeline  
**Performance Goals**: Prepare both source collections in one repeatable flow; preserve retrieval/training usability without manual path edits; keep sync workflow short and subset-friendly  
**Constraints**: Must keep work inside `repos/fungal-cv-qdrant` plus shared Dataset/docs; must not break retrieval holdout flow; must support cases where YOLO backend is unavailable; must remove redundant top-level artifact copies rather than add more compatibility layers  
**Scale/Scope**: One experiment repo, root Dataset artifacts, one unified preparation pipeline, all downstream consumers in fungal-cv-qdrant that currently assume `Dataset/original`, `Dataset/new_data`, `full_image`, or `segmented_image`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: touched code stays in `repos/fungal-cv-qdrant` plus shared root `Dataset/` docs/tooling; backend/frontend not changed.
- [x] Traceability is explicit: retrieval consumer is `repos/fungal-cv-qdrant/src/experiments/retrieval/run.py`; producer is unified dataset-preparation command replacing `src.utils.reformat_dataset` and `src.utils.reformat_dataset_yolo`; consumed artifacts are canonical hierarchical images, per-method segment outputs, visualization artifacts, mapping CSV, and retained metadata records.
- [x] Reimplementation is explicit: no backend/frontend reimplementation boundary applies because feature stays in experiment repo.
- [x] Canonical toolchains are explicit: Python work uses `uv`/`uvx`; GitHub checks use `gh` only if needed.
- [x] Validation is explicit: exact commands listed in quickstart and done criteria for preparation, retrieval smoke checks, lint/type checks, and sync tests if touched.
- [x] Definition of done is explicit: local checks, manual dataset-tree inspection, segmentation artifact inspection, and sync dry-run evidence are named.
- [x] Contract sync is explicit: `repos/fungal-cv-qdrant/README.md`, sync examples, and any dataset-path-facing experiment docs must be updated with new canonical names and artifact rules.
- [x] Minimality is justified: plan avoids touching backend/frontend and replaces duplicate preparation scripts with one schema instead of adding compatibility layers.

## Project Structure

### Documentation (this feature)

```text
specs/005-dataset-restructure/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
repos/fungal-cv-qdrant/
├── src/config.py
├── src/prepare/
├── src/utils/
├── src/experiments/
├── src/analysis/
└── README.md

Dataset/
├── [renamed source collections]
├── [canonical derived hierarchy]
└── [retained mapping/feature metadata artifacts]

tools/
└── dataset_sync.py
```

### Affected Repositories

| Repo Path | Type | Reason |
|-----------|------|--------|
| repos/fungal-cv-qdrant | submodule | Owns dataset preparation, retrieval/training consumers, config, and user-facing dataset documentation |

**Structure Decision**: Edit `repos/fungal-cv-qdrant/src/config.py`, unified preparation code under `src/utils/` or `src/prepare/`, downstream consumers in `src/experiments/`, `src/analysis/`, and `src/utils/`, plus `repos/fungal-cv-qdrant/README.md` and root sync examples as needed. Artifact boundary stays at shared `Dataset/` and `tools/dataset_sync.py` usage docs.

## Phase 0: Research Summary

Research captured in `research.md` resolves required design choices:
- canonical naming for source collections
- canonical artifact schema for per-image outputs
- retrieval/training contract after flat segment removal
- sync/documentation surface that must change after restructure

## Phase 1: Design Summary

Design artifacts define:
- canonical dataset entities and relationships in `data-model.md`
- filesystem contract for prepared images, per-method segments, visualizations, and retained metadata in `contracts/dataset-layout.md`
- operator workflow in `quickstart.md`

## Post-Design Constitution Check

- [x] Ownership remains explicit and limited to experiment repo plus shared dataset artifacts.
- [x] Producer/consumer traceability is documented through canonical preparation outputs and retrieval consumers.
- [x] No direct cross-repo imports or new shared runtime coupling introduced.
- [x] Canonical toolchains remain `uv`/`uvx` and existing shell/rclone workflows.
- [x] Validation and manual evidence remain explicit.
- [x] Documentation/sync contract updates are included in scope.
- [x] No unjustified complexity or compatibility layer added.

## Complexity Tracking

No constitution violations requiring justification.
