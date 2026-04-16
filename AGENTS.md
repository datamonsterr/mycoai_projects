# MycoAI Monorepo

## Layout

```
/home/dat/dev/mycoai/
├── fungal-cv-qdrant/   # Git submodule: fungal CV + Qdrant codebase
├── mycoai_retrieval_backend/   # Git submodule: FastAPI retrieval backend
├── mycoai_retrieval_frontend/  # Git submodule: React retrieval frontend
├── Dataset/            # Shared datasets for the monorepo
├── results/            # Shared experiment outputs and logs
├── weights/            # Shared model checkpoints
├── species_weights.json
├── .agents/
├── .claude/
└── .opencode/
```

## Working Rules

- Code paths like `src/`, `docs/`, and `report/` refer to `fungal-cv-qdrant/` unless the backend/frontend repo is explicitly named.
- Shared runtime data lives at the monorepo root in `Dataset/`, `results/`, `weights/`, `.qdrant_storage/`, and `species_weights.json`.
- Python workflows in this monorepo use `uv`/`uvx`; frontend package workflows use `pnpm`.
- GitHub workflow, checks, and PR automation use `gh`.
- Agent configuration lives at the monorepo root in `.agents/`, `.claude/`, `.opencode/`, `AGENTS.md`, and `CLAUDE.md`.
- `mycoai_retrieval_backend/` and `mycoai_retrieval_frontend/` consume validated outputs from `fungal-cv-qdrant/src/experiments/retrieval/` and `fungal-cv-qdrant/src/experiments/kmeans_segmentation/`; keep producer and consumer docs in sync when those contracts change.
- Product repos MAY inspect experiment code to understand behavior, but they MUST reimplement that behavior locally and MUST NOT import directly from `fungal-cv-qdrant/`.

## Common Commands

```bash
# Install Python dependencies for fungal-cv-qdrant
uv --directory fungal-cv-qdrant sync

# Run one autoresearch experiment
uv --directory fungal-cv-qdrant run python src/prepare.py --experiment threshold

# List available experiments
uv --directory fungal-cv-qdrant run python src/run.py --experiment-list

# Install backend and frontend dependencies
uv --directory mycoai_retrieval_backend sync --all-groups
pnpm --dir mycoai_retrieval_frontend install

# Install toolchain and start local Qdrant
mise install
mise run qdrant-up
```

## Notes

- `fungal-cv-qdrant/src/config.py` resolves the monorepo root automatically when the submodule is used inside this workspace.
- The threshold staircase chart still writes to `results/autoresearch/{experiment}.csv` and `.png` at the monorepo root.
- The backend and frontend repos are standalone deployable projects but live in this monorepo as sibling submodules.
- User-facing product changes are only done after local checks, relevant workflow checks, and manual browser or API validation are recorded.
- Detailed project guidance remains in `CLAUDE.md` and `fungal-cv-qdrant/README.md`.

## Active Technologies
- Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib (001-yolo-dataset-tools)
- Local filesystem under `Dataset/original/` and a user-supplied export path (001-yolo-dataset-tools)

## Recent Changes
- 001-yolo-dataset-tools: Added Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib
