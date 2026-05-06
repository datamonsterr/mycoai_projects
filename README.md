# MycoAI Monorepo

MycoAI is a monorepo that coordinates one experiment repository and two product
repositories, plus shared datasets, results, and weights at the workspace root.
The three git submodules now live under `repos/`.

## Repository Layout

```text
/home/dat/dev/mycoai/
├── repos/
│   ├── fungal-cv-qdrant/           # Experiment + analysis code
│   ├── mycoai_retrieval_backend/   # FastAPI retrieval backend
│   └── mycoai_retrieval_frontend/  # React 19 + Vite frontend
├── Dataset/                        # Shared datasets
├── results/                        # Shared outputs, logs, reports
├── weights/                        # Shared checkpoints
├── species_weights.json            # Shared lookup artifact
├── tools/                          # Shared workspace/bootstrap/sync tooling
├── specs/                          # Spec-kit feature artifacts
├── AGENTS.md
├── CLAUDE.md
└── mise.toml
```

## Ownership

- `repos/fungal-cv-qdrant/` owns experiment logic, reports, and artifact
  generation.
- `repos/mycoai_retrieval_backend/` owns backend APIs, indexing, and product-side
  service behavior.
- `repos/mycoai_retrieval_frontend/` owns scientist-facing UI behavior.
- `Dataset/`, `results/`, `weights/`, and `species_weights.json` are shared
  runtime artifacts, not shared code locations.

Product repos may inspect experiment code for reference, but they must
reimplement behavior locally and must not import runtime code from
`repos/fungal-cv-qdrant/`.

## Prerequisites

- `git` with submodule support
- `mise`
- `uv`
- `pnpm`
- `gh`

Install toolchains:

```bash
mise install
```

## Initial Setup

For a fresh clone or a new git worktree, run the init flow before feature work:

```bash
git submodule update --init --recursive
git fetch origin
mise trust
uv --directory repos/mycoai_retrieval_backend sync --all-groups
pnpm --dir repos/mycoai_retrieval_frontend install
uv --directory repos/fungal-cv-qdrant sync
```

If you are on `main`, also fast-forward it:

```bash
git pull --ff-only origin main
```

If these files exist and their `.env` counterparts do not, copy them manually
before starting work:

- `repos/mycoai_retrieval_backend/.env.example`
- `repos/mycoai_retrieval_frontend/.env.example`
- `.env.example`

Enter credentials manually after copying.

## Common Commands

### Experiment repo

```bash
uv --directory repos/fungal-cv-qdrant sync
uv --directory repos/fungal-cv-qdrant run python src/prepare.py --experiment threshold
uv --directory repos/fungal-cv-qdrant run python src/run.py --experiment-list
```

### Backend repo

```bash
uv --directory repos/mycoai_retrieval_backend sync --all-groups
uv --directory repos/mycoai_retrieval_backend run ruff check .
uv --directory repos/mycoai_retrieval_backend run ruff format --check .
uv --directory repos/mycoai_retrieval_backend run mypy src
uv --directory repos/mycoai_retrieval_backend run pytest
```

### Frontend repo

```bash
pnpm --dir repos/mycoai_retrieval_frontend install
pnpm --dir repos/mycoai_retrieval_frontend lint
pnpm --dir repos/mycoai_retrieval_frontend typecheck
pnpm --dir repos/mycoai_retrieval_frontend build
```

## Dataset Structure

Dataset root defaults to `Dataset/` at the monorepo root. Override with
`DATASET_ROOT` environment variable. Structure must preserve:

```text
Dataset/
├── curated_primary/          # High-quality source images (~4-7 strains/species)
│   └── {species}/{strain}/   # Used for holdout, retrieval, YOLO training
├── incoming_low_quality/     # Lower-quality source images (~1-2 strains/species)
│   └── {species}/{strain}/   # Diverse data: fewer environments, varied quality
└── prepared/                 # Canonical derived hierarchy
    └── {species}/{strain}/{environment}/{image_stem}/
        ├── source.jpg
        ├── prepared.jpg
        ├── item.json
        ├── segments_kmeans/seg_0.jpg, seg_1.jpg, seg_2.jpg
        ├── segments_contour/seg_0.jpg, ...
        ├── bbox_kmeans.jpg
        ├── bbox_contour.jpg
        ├── pipeline_kmeans.jpg
        └── pipeline_contour.jpg
```

Legacy paths `Dataset/original/` and `Dataset/new_data/` still work as fallback
when canonical paths don't exist.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MYCOAI_ROOT` | Auto-detected monorepo root | Workspace root directory |
| `DATASET_ROOT` | `$MYCOAI_ROOT/Dataset` | Path to shared Dataset folder |
| `WEIGHTS_DIR` | `$MYCOAI_ROOT/weights` | Path to model checkpoints |
| `RESULTS_DIR` | `$MYCOAI_ROOT/results` | Path to experiment outputs |

Set `DATASET_ROOT` to a different path when using external storage:

```bash
export DATASET_ROOT=/mnt/data/fungal-dataset
```

### Shared workspace tooling

```bash
bash tools/workspace_bootstrap.sh prepare
bash tools/workspace_bootstrap.sh smoke-check
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>

uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py export --remote mydrive:mycoai-dataset --scope prepared/segments
```

## Vast.ai Remote Workspace Setup

### Quick Setup (First Time)

1. Rent or reuse a Vast.ai instance with SSH access.
2. SSH to the machine and clone the monorepo into the target workspace root.
3. From the monorepo root, run prepare:

```bash
bash tools/workspace_bootstrap.sh prepare --non-interactive \
  --ssh-host <host> --ssh-user <user> --ssh-port <port> \
  --instance-id <vast-instance-id>
```

4. Validate the workspace:

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

5. Use the printed connection descriptor to connect from VS Code Remote-SSH.

**Unavoidable manual steps** (required before automation can proceed):
- Choose and rent a Vast.ai instance with SSH access
- Attach your SSH key in the Vast.ai account panel
- Authorize VS Code Remote-SSH host key on first connect

### Recover After Restart or Replacement

If the instance changes host or port after a restart:

```bash
# Rediscover SSH details from the Vast.ai UI or CLI, then:
bash tools/workspace_bootstrap.sh recover \
  --instance-id <vast-instance-id> \
  --host <new-host> --port <new-port>
```

The recovery command re-validates the workspace, repairs submodules, re-syncs
missing venvs, and prints an updated connection descriptor for VS Code.

### Workspace Bootstrap Script Reference

```bash
# Prepare a fresh workspace
bash tools/workspace_bootstrap.sh prepare [--non-interactive] \
  [--ssh-host <host>] [--ssh-user <user>] [--ssh-port <port>] \
  [--instance-id <id>] [--workspace-root <path>]

# Validate workspace readiness
bash tools/workspace_bootstrap.sh smoke-check

# Revalidate after reconnect
bash tools/workspace_bootstrap.sh recover \
  [--instance-id <id>] [--host <host>] [--port <port>] \
  [--user <user>] [--workspace-root <path>]

# Show help
bash tools/workspace_bootstrap.sh help
```

### Setup Completion Criteria

Setup is complete when all of the following are true:
- `prepare` finished without blocking errors
- `smoke-check` passed (validated status)
- Connection descriptor is printed and usable for VS Code Remote-SSH
- VS Code opens the correct remote workspace root
- Any remaining manual steps are documented, not unresolved gaps

## Path Conventions

- Unqualified `src/`, `docs/`, `report/`, and `pyproject.toml` references mean
  `repos/fungal-cv-qdrant/` unless another repo is named explicitly.
- Product-side features that depend on experiment outputs must name the producer
  command, consumed artifact, and downstream consumer in spec, plan, and task
  artifacts.
- The autoresearch branch naming and staircase-chart rules apply only to
  `repos/fungal-cv-qdrant/` experiment work.

## Notes

- `repos/fungal-cv-qdrant/src/config.py` auto-detects the monorepo root when the
  submodule lives under `repos/`; `MYCOAI_ROOT` overrides auto-detection.
- `DATASET_ROOT` env var lets shared dataset live outside the monorepo (e.g.
  external SSD, Vast.ai volume); folder structure must match the canonical layout.
- Shared remote-workspace bootstrap and dataset sync entrypoints live in
  `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py`.
- GitHub automation should use `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh ...`
  when project guidance requires the isolated profile.
