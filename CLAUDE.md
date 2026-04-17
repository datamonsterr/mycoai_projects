# CLAUDE.md

This file provides guidance for working in the MycoAI monorepo.

## Monorepo Structure

```
/home/dat/dev/mycoai/
├── fungal-cv-qdrant/   # Git submodule with the fungal CV codebase
├── mycoai_retrieval_backend/   # FastAPI backend repo
├── mycoai_retrieval_frontend/  # React + shadcn frontend repo
├── Dataset/            # Shared datasets
├── results/            # Shared outputs, logs, charts
├── weights/            # Shared checkpoints
├── species_weights.json
├── .agents/
├── .claude/
└── .opencode/
```

## Path Conventions

- `src/`, `docs/`, `report/`, and `pyproject.toml` live under `fungal-cv-qdrant/`.
- `mycoai_retrieval_backend/` is an independent FastAPI service repo.
- `mycoai_retrieval_frontend/` is an independent React frontend repo.
- `Dataset/`, `results/`, `weights/`, and `species_weights.json` live at the monorepo root.
- Python workflows use `uv`/`uvx`; frontend package workflows use `pnpm`.
- GitHub workflow, checks, and PR automation use `gh`.
- Agent configuration is shared at the monorepo root.
- The `.opencode/rules/branch-naming.md` and `.opencode/rules/experiment-visualization.md` files apply only to `fungal-cv-qdrant/` autoresearch work, not to backend, frontend, or general monorepo branches and charts.
- Product repos may inspect `fungal-cv-qdrant` experiments for reference, but they must reimplement locally and must not import from that repo directly.

## Core Workflow

```bash
# Install toolchain and sync dependencies
mise install
mise run sync

# Start Qdrant
mise run qdrant-up

# Run prepare + experiment checks
uv --directory fungal-cv-qdrant run python src/prepare.py --experiment threshold

# Run a direct experiment
uv --directory fungal-cv-qdrant run python src/run.py --experiment threshold

# Full prepare pipeline
uv --directory fungal-cv-qdrant run python -m src.prepare.init --collection myco_fungi_features_full

# Backend and frontend
uv --directory mycoai_retrieval_backend sync --all-groups
pnpm --dir mycoai_retrieval_frontend install
pnpm --dir mycoai_retrieval_frontend run dev

# Prepare and validate a remote-style workspace from the monorepo root
bash tools/workspace_bootstrap.sh prepare
bash tools/workspace_bootstrap.sh smoke-check
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>

# Preview and run dataset sync commands
uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope original/sample
uv run python tools/dataset_sync.py import --remote mydrive:mycoai-dataset --scope original/sample
uv run python tools/dataset_sync.py export --remote mydrive:mycoai-dataset --scope segmented_image/new-batch

# Upload features from the shared dataset root
uv --directory fungal-cv-qdrant run python -m src.utils.upload_qdrant \
  --features-json ../Dataset/segmented_features.json \
  --metadata-json ../Dataset/segmented_image_metadata.json \
  --collection myco_fungi_features_full
```

## Project Notes

- `fungal-cv-qdrant/src/config.py` auto-detects this monorepo layout and resolves shared paths from the parent workspace.
- Threshold autoresearch artifacts are written to `results/autoresearch/` at the monorepo root.
- Qdrant storage persists at the monorepo root in `.qdrant_storage/`.
- Shared remote-workspace bootstrap and dataset sync entrypoints live at `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py`.
- `mise install` now installs `rclone` for dataset sync, but the Google Drive remote configuration still lives outside the repo via `RCLONE_CONFIG` or the default `~/.config/rclone/rclone.conf`.
- User-facing backend and frontend work is expected to carry local validation, relevant workflow checks, and a manual browser or API journey check before PR handoff.
- Detailed project-specific docs remain in `fungal-cv-qdrant/README.md` and `fungal-cv-qdrant/docs/`.
