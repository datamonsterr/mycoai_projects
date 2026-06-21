# Monorepo Flattening Refactor Design

Date: 2026-06-03

## Goal

Convert MycoAI from a submodule-based monorepo into a flat source tree. Existing implementation code is migrated as normal files. Git history from submodules is not preserved.

## Final Layout

- `frontend/` contains the existing `prototype/` implementation, renamed in place.
- `backend/` contains the existing `repos/backend/` implementation.
- `research/` contains the existing `repos/fungal-cv-qdrant/` experiment implementation.
- `repos/` is removed after migration.
- `.gitmodules` is removed.
- `repos/mycoai_retrieval_frontend/` is removed and not migrated.

## Files Kept And Updated

These root files and directories must remain:

- `mise.toml`
- `.opencode/`
- `.agents/`
- `AGENTS.md`
- `CLAUDE.md`
- `docs/`
- `tools/`

They are updated to use the new flat paths and to remove submodule instructions.

## Path Rewrite Rules

- `repos/fungal-cv-qdrant` -> `research`
- `repos/mycoai_retrieval_backend` -> `backend`
- `repos/mycoai_retrieval_frontend` -> `frontend` only where it refers to the active frontend product; otherwise remove stale references.
- `prototype` -> `frontend`
- `fungal-cv-qdrant` remains only as historical experiment/research name where semantically needed, not as a filesystem path.
- Submodule setup, submodule branch alignment, and submodule checkout instructions are removed.

## `mise.toml` Design

`mise.toml` stays as the root task registry. It is rewritten to use flat paths:

- Research Python environment: `research/.venv`
- Research sync: `uv --directory research sync`
- Qdrant compose: `research/docker-compose.yml`
- Threshold experiment: `uv --directory research run python src/prepare.py --experiment threshold`
- Experiment list: `uv --directory research run python src/run.py --experiment-list`
- Backend sync/checks: `uv --directory backend ...`
- Frontend install/checks: `pnpm --dir frontend ...`
- Project init: no `git submodule update`; install tools and dependencies only.
- Remove submodule branch tasks.

## Documentation And Agent Instruction Design

Update docs and agent instructions to describe the flat tree:

- `research/` is producer of validated experiment artifacts.
- `backend/` and `frontend/` are product implementations.
- Product code may inspect `research/` but must not import runtime code from it unless a future shared package is explicitly created.
- Dataset/results/weights remain root shared runtime data.
- Commands use `research`, `backend`, and `frontend` paths.
- Stale docs whose main purpose is submodule setup or submodule coordination are removed.

## Migration Flow

1. Verify git status and preserve existing uncommitted root changes.
2. Move `prototype/` to `frontend/`.
3. Copy or move submodule working trees into root as normal directories:
   - `repos/backend/` -> `backend/`
   - `repos/fungal-cv-qdrant/` -> `research/`
4. Remove nested git metadata from migrated directories.
5. Remove `.gitmodules`.
6. Remove `repos/`.
7. Rewrite root docs, instructions, `mise.toml`, tool scripts, and opencode config paths.
8. Search for stale path references and resolve each intentionally.
9. Run validation.

## Validation

Run all relevant checks after migration:

- `mise run project-init`
- `mise run backend-lint`
- `mise run frontend-lint`
- `uv --directory research run pytest tests/ -q`
- `uv --directory research run python -m ruff check src/experiments/`
- Existing workspace/dataset smoke commands where path changes affect them.

If a check fails because of pre-existing code issues, record the exact failure and whether the migration changed it.

## Risks

- Existing root has uncommitted doc/context changes. Migration must not overwrite them.
- Nested `.git` metadata inside submodule directories must be removed before staging.
- Existing docs may contain many semantic references to old repo names. Path references must be rewritten; historical project names may remain only when not misleading.
- `prototype/` and `repos/mycoai_retrieval_frontend/` may both be frontend implementations. The requested source of truth is `prototype/`, so the old frontend submodule is removed.
