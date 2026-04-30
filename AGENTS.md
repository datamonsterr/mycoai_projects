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
- GitHub workflow, checks, and PR automation use `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh <args>`, authenticated as `datamonsterr`; do not use `gh auth switch` because it mutates shared state and can race with other project agents.
- Agent configuration lives at the monorepo root in `.agents/`, `.claude/`, `.opencode/`, `AGENTS.md`, and `CLAUDE.md`.
- The `.opencode/rules/branch-naming.md` and `.opencode/rules/experiment-visualization.md` rules apply only to `fungal-cv-qdrant/` autoresearch work, not to backend, frontend, or general monorepo branches and charts.
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

# Prepare and validate a remote-style workspace from the monorepo root
bash tools/workspace_bootstrap.sh prepare
bash tools/workspace_bootstrap.sh smoke-check
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>

# Preview and run dataset sync commands
uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope original/sample
uv run python tools/dataset_sync.py import --remote mydrive:mycoai-dataset --scope original/sample
uv run python tools/dataset_sync.py export --remote mydrive:mycoai-dataset --scope segmented_image/new-batch
```

## Notes

- `fungal-cv-qdrant/src/config.py` resolves the monorepo root automatically when the submodule is used inside this workspace.
- The threshold staircase chart still writes to `results/autoresearch/{experiment}.csv` and `.png` at the monorepo root.
- Shared remote-workspace bootstrap and dataset sync entrypoints live at `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py`.
- For a fresh clone or a newly created git worktree, run `/init` before project work. The init flow updates submodules, refreshes from `origin`, fast-forwards `main` when applicable, prepares missing backend and frontend `.env` files, installs backend dependencies with `uv`, installs frontend dependencies with `pnpm`, runs `mise trust`, copies root `.env.example` when present, and reminds the user to enter credentials manually.
- `mise install` now installs `rclone` for dataset sync, but the Google Drive remote configuration still lives outside the repo via `RCLONE_CONFIG` or the default `~/.config/rclone/rclone.conf`.
- The backend and frontend repos are standalone deployable projects but live in this monorepo as sibling submodules.
- User-facing product changes are only done after local checks, relevant workflow checks, and manual browser or API validation are recorded.
- Detailed project guidance remains in `CLAUDE.md` and `fungal-cv-qdrant/README.md`.
- Terse by default: keep agent output compact, load only needed repo context, and prefer codebase-memory MCP for broad code structure queries before file-by-file reads.

## Active Technologies
- Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib (001-yolo-dataset-tools)
- Local filesystem under `Dataset/original/` and a user-supplied export path (001-yolo-dataset-tools)
- Bash + Python 3.13 + OpenSSH, git with submodules, `mise`, `uv`, `rclone`, optional `vastai` CLI for connection lookup (001-vastai-workspace-sync)
- Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), Google Drive remote rooted to a dedicated dataset folder, ephemeral Vast.ai instance storage with optional external persistence (001-vastai-workspace-sync)
- Bash + Python 3.13 + Markdown documentation + OpenSSH, git with submodules, `mise`, `uv`, optional `vastai` CLI for instance lookup, VS Code Remote-SSH, existing `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py` (001-vastai-workspace-sync)
- Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), local SSH config on the developer machine, optional external `rclone` config for dataset access (001-vastai-workspace-sync)

## Recent Changes
- 001-yolo-dataset-tools: Added Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib
