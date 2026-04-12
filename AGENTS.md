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
- Shared runtime data lives at the monorepo root in `Dataset/`, `results/`, `weights/`, and `species_weights.json`.
- Agent configuration lives at the monorepo root in `.agents/`, `.claude/`, `.opencode/`, `AGENTS.md`, and `CLAUDE.md`.

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
npm --prefix mycoai_retrieval_frontend install

# Install toolchain and start local Qdrant
mise install
mise run qdrant-up
```

## Notes

- `fungal-cv-qdrant/src/config.py` resolves the monorepo root automatically when the submodule is used inside this workspace.
- The threshold staircase chart still writes to `results/autoresearch/{experiment}.csv` and `.png` at the monorepo root.
- The backend and frontend repos are standalone deployable projects but live in this monorepo as sibling submodules.
- Detailed project guidance remains in `CLAUDE.md` and `fungal-cv-qdrant/README.md`.
