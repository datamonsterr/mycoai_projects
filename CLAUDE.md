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
- Agent configuration is shared at the monorepo root.

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
npm --prefix mycoai_retrieval_frontend install
npm --prefix mycoai_retrieval_frontend run dev

# Upload features from the shared dataset root
uv --directory fungal-cv-qdrant run python -m src.utils.upload_qdrant \
  --features-json ../Dataset/segmented_features.json \
  --metadata-json ../Dataset/segmented_image_metadata.json \
  --collection myco_fungi_features_full
```

## Project Notes

- `fungal-cv-qdrant/src/config.py` auto-detects this monorepo layout and resolves shared paths from the parent workspace.
- Threshold autoresearch artifacts are written to `results/autoresearch/` at the monorepo root.
- Qdrant storage remains inside `fungal-cv-qdrant/qdrant_storage/`.
- Detailed project-specific docs remain in `fungal-cv-qdrant/README.md` and `fungal-cv-qdrant/docs/`.
