# MycoAI Project Overview

## Repository Structure

This is a monorepo for the MycoAI project — a fungal species identification system using computer vision and vector retrieval (Qdrant).

Key directories:

| Directory | Purpose |
|-----------|---------|
| `backend/` | Python FastAPI backend |
| `mycoai_retrieval_frontend/` | React 19 + Vite frontend |
| `research/` | Experiment code (submodule: fungal-cv-qdrant) |
| `graduation_report/` | LaTeX graduation thesis source |
| `docs/graduation_report/` | Report control plane (reviews, plans, rules) |
| `Dataset/` | Image data (gitignored, synced via rclone) |
| `results/` | Experiment outputs (gitignored) |
| `weights/` | Model weights (gitignored) |
| `tools/` | Workspace bootstrap and utility scripts |

## Toolchain

- **Python**: managed by `uv` — always use `uv run` for Python commands
- **Frontend**: managed by `pnpm`
- **Experiments**: `uv --directory research ...` or `uv --directory fungal-cv-qdrant ...`
- **LaTeX**: TinyTeX with pdflatex, built via `./render.sh`
- **Docker**: Qdrant via `docker compose up -d`
- **Remote GPU**: Vast.ai instances at `/workspace/mycoai`

## Key Commands

```bash
# Backend
uv --directory backend sync --all-groups
uv --directory backend run pytest
uv --directory backend run ruff check
uv --directory backend run mypy .

# Frontend
pnpm --dir mycoai_retrieval_frontend install
pnpm --dir mycoai_retrieval_frontend lint
pnpm --dir mycoai_retrieval_frontend typecheck
pnpm --dir mycoai_retrieval_frontend build

# Experiments
uv run python src/run.py --experiment <name> --description "change description"
uv run python src/prepare.py --experiment <name>

# LaTeX
./render.sh                          # full render
./render.sh --clean                  # clean artifacts

# Qdrant
docker compose up -d                 # start
docker compose down                  # stop
```

## Python Environment

Always use `uv run` for all Python commands. Never use bare `python` or `source .venv/bin/activate` in scripts.

```bash
# CORRECT
uv run python src/main.py
uv sync                    # install deps
uv add <package>           # add dependency
uv add --dev <package>     # add dev dep

# WRONG
python src/main.py
pip install <package>
```
