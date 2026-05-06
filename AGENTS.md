# MycoAI Monorepo

## Layout

```
/home/dat/dev/mycoai/
├── repos/fungal-cv-qdrant/   # Git submodule: fungal CV + Qdrant codebase
├── repos/mycoai_retrieval_backend/   # Git submodule: FastAPI retrieval backend
├── repos/mycoai_retrieval_frontend/  # Git submodule: React retrieval frontend
├── Dataset/            # Shared datasets for the monorepo
├── results/            # Shared experiment outputs and logs
├── weights/            # Shared model checkpoints
├── species_weights.json
├── .agents/
├── .claude/
└── .opencode/
```

## Working Rules

- Code paths like `src/`, `docs/`, and `report/` refer to `repos/fungal-cv-qdrant/` unless the backend/frontend repo is explicitly named.
- Shared runtime data lives at the monorepo root in `Dataset/`, `results/`, `weights/`, `.qdrant_storage/`, and `species_weights.json`.
- Python workflows in this monorepo use `uv`/`uvx`; frontend package workflows use `pnpm`.
- GitHub workflow, checks, and PR automation use `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh <args>`, authenticated as `datamonsterr`; do not use `gh auth switch` because it mutates shared state and can race with other project agents.
- Agent configuration lives at the monorepo root in `.agents/`, `.claude/`, `.opencode/`, `AGENTS.md`, and `CLAUDE.md`.
- The `.opencode/rules/branch-naming.md` and `.opencode/rules/experiment-visualization.md` rules apply only to `repos/fungal-cv-qdrant/` autoresearch work, not to backend, frontend, or general monorepo branches and charts.
- `repos/mycoai_retrieval_backend/` and `repos/mycoai_retrieval_frontend/` consume validated outputs from `repos/fungal-cv-qdrant/src/experiments/retrieval/` and `repos/fungal-cv-qdrant/src/experiments/kmeans_segmentation/`; keep producer and consumer docs in sync when those contracts change.
- Product repos MAY inspect experiment code to understand behavior, but they MUST reimplement that behavior locally and MUST NOT import directly from `repos/fungal-cv-qdrant/`.

## Common Commands

```bash
# Install Python dependencies for fungal-cv-qdrant
uv --directory repos/fungal-cv-qdrant sync

# Run one autoresearch experiment
uv --directory repos/fungal-cv-qdrant run python src/prepare.py --experiment threshold

# List available experiments
uv --directory repos/fungal-cv-qdrant run python src/run.py --experiment-list

# Install backend and frontend dependencies
uv --directory repos/mycoai_retrieval_backend sync --all-groups
pnpm --dir repos/mycoai_retrieval_frontend install

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

- `repos/fungal-cv-qdrant/src/config.py` resolves the monorepo root automatically when the submodule is used inside this workspace.
- The threshold staircase chart still writes to `results/autoresearch/{experiment}.csv` and `.png` at the monorepo root.
- Shared remote-workspace bootstrap and dataset sync entrypoints live at `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py`.
- For a fresh clone or a newly created git worktree, run `/init` before project work. The init flow updates submodules, refreshes from `origin`, fast-forwards `main` when applicable, prepares missing backend and frontend `.env` files, installs backend dependencies with `uv`, installs frontend dependencies with `pnpm`, runs `mise trust`, copies root `.env.example` when present, and reminds the user to enter credentials manually.
- `mise install` now installs `rclone` for dataset sync, but the Google Drive remote configuration still lives outside the repo via `RCLONE_CONFIG` or the default `~/.config/rclone/rclone.conf`.
- The backend and frontend repos are standalone deployable projects but live in this monorepo as sibling submodules.
- User-facing product changes are only done after local checks, relevant workflow checks, and manual browser or API validation are recorded.
- Detailed project guidance remains in `CLAUDE.md` and `repos/fungal-cv-qdrant/README.md`.
- Terse by default: keep agent output compact, load only needed repo context, and prefer codebase-memory MCP for broad code structure queries before file-by-file reads.
- Vast.ai remote workspace setup: use the canonical `tools/workspace_bootstrap.sh` entrypoint. Completion criteria: prepare finished without blockers, smoke-check passed, connection descriptor printed and usable for VS Code, and VS Code opens the correct remote workspace root. Agents must call out unavoidable manual steps (instance rental, SSH key registration, VS Code host key authorization) before starting automation.

## Active Technologies
- Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib (001-yolo-dataset-tools)
- Local filesystem under `Dataset/original/` and a user-supplied export path (001-yolo-dataset-tools)
- Bash + Python 3.13 + OpenSSH, git with submodules, `mise`, `uv`, `rclone`, optional `vastai` CLI for connection lookup (001-vastai-workspace-sync)
- Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), Google Drive remote rooted to a dedicated dataset folder, ephemeral Vast.ai instance storage with optional external persistence (001-vastai-workspace-sync)
- Bash + Python 3.13 + Markdown documentation + OpenSSH, git with submodules, `mise`, `uv`, optional `vastai` CLI for instance lookup, VS Code Remote-SSH, existing `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py` (001-vastai-workspace-sync)
- Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), local SSH config on the developer machine, optional external `rclone` config for dataset access (001-vastai-workspace-sync)

## Autolab Multi-Agent System (004-autolab-multi-agent)

Five-agent orchestration layer built on top of `fungal-cv-qdrant` autoresearch infrastructure.

### Agent Roster

| Agent | Model | Mode | Role |
|-------|-------|------|------|
| `autolab` | `9router/BigBrain` | primary | Orchestrator — delegates to all subagents |
| `researcher` | `9router/BigBrain` | subagent | Literature scout — web/PDF → paper-ideas.md |
| `planner` | `9router/MidBrain` | subagent | Queue coordinator — assigns run_ids to Workers |
| `worker` | `9router/MiniBrain` | subagent | Isolated experiment runner via git worktree |
| `reporter` | `9router/MiniBrain` | subagent | Status summarizer — reads CSV, emits F1 summary |

### Invocation

```bash
# Launch opencode and prompt the Autolab agent
opencode
# Prompt: "run one autoresearch pass on retrieval experiment"
```

### Test Command

```bash
# Run all autolab tests + lint
uv --directory repos/fungal-cv-qdrant run pytest tests/ -q
uv --directory repos/fungal-cv-qdrant run python -m ruff check src/experiments/
```

Or use the registered command: `opencode run "test"`

### Key Files

- Agent definitions: `.opencode/agents/autolab.md`, `researcher.md`, `planner.md`, `worker.md`, `reporter.md`
- Custom tools: `.opencode/tools/hypothesis-validator.ts`, `experiment-test-runner.ts`
- Plugin: `.opencode/plugins/autolab-compaction.ts`
- Research notebook: `repos/fungal-cv-qdrant/research/`
- Worker runtime: `repos/fungal-cv-qdrant/.runtime/worktrees/` (gitignored)

### Worktree Lifecycle

Workers create `repos/fungal-cv-qdrant/.runtime/worktrees/<experiment-id>` per run.
Worktrees are removed after the run completes. Best-result worktrees are retained until merged.
Max concurrent workers: `MAX_CONCURRENT_WORKERS=2` (default).

## Recent Changes
- 004-autolab-multi-agent: Added 5-agent Autolab orchestration layer, custom tools/plugin, and full spec/plan/tasks package
- 001-yolo-dataset-tools: Added Python 3.13 + OpenCV, NumPy, pandas, scikit-learn, pathlib
