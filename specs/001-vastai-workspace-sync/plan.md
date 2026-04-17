# Implementation Plan: Vast.ai Workspace Bootstrap and Dataset Sync

**Branch**: `001-vastai-workspace-sync` | **Date**: 2026-04-17 | **Spec**: `/home/dat/dev/mycoai/specs/001-vastai-workspace-sync/spec.md`
**Input**: Feature specification from `/specs/001-vastai-workspace-sync/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Create monorepo-level `tools/` utilities and operator docs that turn a fresh
Vast.ai instance into a usable MycoAI workspace, support VSCode Remote-SSH
access, and provide safe `Dataset/` import/export workflows against Google
Drive. The implementation will keep shared-path logic at the monorepo root, use
shell for workspace orchestration, use a small Python CLI for dataset sync
planning and reporting around `rclone`, and expose repeatable smoke-check and
recovery flows.

## Technical Context

**Language/Version**: Bash + Python 3.13  
**Primary Dependencies**: OpenSSH, git with submodules, `mise`, `uv`, `rclone`, optional `vastai` CLI for connection lookup  
**Package / Command Tooling**: `uv`/`uvx` for Python execution, `mise` for shared entrypoints, `pnpm` only when downstream frontend dependencies are installed, `gh` unchanged for workflow operations  
**Storage**: Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), Google Drive remote rooted to a dedicated dataset folder, ephemeral Vast.ai instance storage with optional external persistence  
**Testing**: `bash -n tools/workspace_bootstrap.sh`, `uv run --with pytest pytest tools/tests/test_dataset_sync.py`, manual fresh-instance bootstrap, sample dry-run import/export, `uv --directory fungal-cv-qdrant sync`, `uv --directory fungal-cv-qdrant run python -m src.prepare.init --help`  
**Target Platform**: Linux GPU instances on Vast.ai plus a local workstation using VSCode Remote-SSH  
**Project Type**: Monorepo root operational tooling + documentation  
**Performance Goals**: Fresh instance to VSCode-ready workspace in <=20 minutes; proof-of-access dataset transfer in <=5 minutes; reconnect/recovery in <=10 minutes  
**Constraints**: New tooling must live in root `tools/`; shared root paths must remain canonical; no runtime imports from submodules; default dataset transfer must be non-destructive and direction-explicit; prefer direct SSH and fall back to proxy SSH only when necessary  
**Scale/Scope**: Single-operator workflow for one rented instance at a time; `Dataset/` may be large enough to require scoped transfers and transfer summaries

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: planned changes stay in shared root assets
      (`tools/`, `mise.toml`, `AGENTS.md`, `CLAUDE.md`) plus
      `fungal-cv-qdrant/README.md`; no backend or frontend code is touched.
- [x] Traceability is explicit: this feature has no dependency on `retrieval` or
      `kmeans_segmentation` artifacts, so no producer/consumer contract boundary
      is crossed.
- [x] Reimplementation is explicit: no backend/frontend behavior is derived from
      experiment code, and no runtime imports from `fungal-cv-qdrant` are
      planned.
- [x] Canonical toolchains are explicit: Python execution uses `uv`, shared task
      entrypoints use `mise`, and any touched frontend bootstrap guidance must
      use `pnpm` instead of raw `npm`.
- [x] Validation is explicit: exact shell, Python, manual bootstrap, and smoke
      commands are listed in Technical Context and Quickstart.
- [x] Definition of done is explicit: unit coverage for sync safeguards, manual
      Vast.ai bootstrap evidence, scoped transfer evidence, and smoke-check
      output are required before handoff.
- [x] Contract sync is explicit: root guidance docs and `fungal-cv-qdrant`
      onboarding docs will be updated to point users at the shared tooling.
- [x] Minimality is justified: shared bootstrap and dataset sync stay at root
      `tools/`; the plan avoids creating a new shared package or service.

Post-design re-check: Pass. The research decisions, data model, CLI contracts,
and quickstart preserve the same ownership, toolchain, and validation
boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/001-vastai-workspace-sync/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── dataset-sync-cli.md
│   └── workspace-bootstrap-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/
├── workspace_bootstrap.sh
├── dataset_sync.py
└── tests/
    └── test_dataset_sync.py

fungal-cv-qdrant/
└── README.md

AGENTS.md
CLAUDE.md
mise.toml
Dataset/
results/
weights/
species_weights.json
```

**Structure Decision**: Root-level `tools/` owns the shared bootstrap and
dataset sync surfaces because they operate on monorepo paths such as `Dataset/`
and `mise.toml`. `fungal-cv-qdrant/README.md` only documents how experiment
workflows consume the prepared workspace. No experiment-to-product artifact
boundary is crossed.

## Complexity Tracking

No constitution exceptions or justified complexity violations are expected for
this feature.
