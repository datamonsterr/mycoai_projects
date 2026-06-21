# Monorepo Flattening Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert MycoAI from submodule-based layout to flat `frontend/`, `backend/`, and `research/` directories with updated commands, docs, tools, and agent instructions.

**Architecture:** Migration is filesystem-first: move existing implementations into root-owned directories, remove nested git metadata, then update all root references. Validation uses existing repo-local commands after paths are rewritten.

**Tech Stack:** Git, Bash, Python 3.13, uv, pnpm, Vite/React, FastAPI/Python backend, mise, opencode agent config.

---

## File Structure

**Create / move:**
- `frontend/` from `prototype/`
- `backend/` from `repos/backend/`
- `research/` from `repos/fungal-cv-qdrant/`

**Remove:**
- `.gitmodules`
- `repos/`
- nested `.git` metadata in `backend/` and `research/`

**Modify:**
- `mise.toml`: flat path tasks
- `AGENTS.md`: flat layout, no submodules
- `CLAUDE.md`: flat layout, no submodules
- `CONTEXT.md`: flat layout references
- `.opencode/agents/*.md`: flat path references
- `.opencode/command/init.md`: init without submodules
- `.opencode/rules/*.md`: flat path scopes and commands
- `tools/workspace_bootstrap.sh`: no submodule setup, flat validation paths
- `tools/dataset_sync.py`: update path help/docs if old paths appear
- `docs/**/*.md`: remove stale submodule docs; rewrite path references
- `README.md`: flat layout and commands

## Task 1: Baseline Safety Snapshot

**Files:**
- Inspect only: root git status and submodule state

- [ ] **Step 1: Record root git status**

Run:
```bash
git status --short --branch
```
Expected: output includes current uncommitted user changes. Do not discard them.

- [ ] **Step 2: Record submodule status**

Run:
```bash
git submodule status || true
```
Expected: lists current submodules or exits safely.

- [ ] **Step 3: Record old path references count**

Run:
```bash
rg -n "repos/fungal-cv-qdrant|repos/mycoai_retrieval_backend|repos/mycoai_retrieval_frontend|git submodule|submodule|prototype" AGENTS.md CLAUDE.md CONTEXT.md README.md docs .opencode tools mise.toml || true
```
Expected: list of stale refs to update later.

## Task 2: Move Implementations Into Flat Layout

**Files:**
- Move: `prototype/` -> `frontend/`
- Move: `repos/backend/` -> `backend/`
- Move: `repos/fungal-cv-qdrant/` -> `research/`
- Remove: `repos/mycoai_retrieval_frontend/`

- [ ] **Step 1: Verify destination names are free**

Run:
```bash
test ! -e frontend && test ! -e backend && test ! -e research
```
Expected: exit code 0. If not, stop and inspect conflicting directory.

- [ ] **Step 2: Move prototype to frontend**

Run:
```bash
mv prototype frontend
```
Expected: `frontend/package.json` exists.

- [ ] **Step 3: Move backend submodule contents**

Run:
```bash
mv repos/mycoai_retrieval_backend backend
```
Expected: `backend/pyproject.toml` exists.

- [ ] **Step 4: Move research submodule contents**

Run:
```bash
mv repos/fungal-cv-qdrant research
```
Expected: `research/pyproject.toml` exists.

- [ ] **Step 5: Remove old frontend submodule and empty repos dir**

Run:
```bash
rm -rf repos/mycoai_retrieval_frontend repos
```
Expected: `test ! -e repos` succeeds.

- [ ] **Step 6: Remove nested git metadata**

Run:
```bash
rm -rf backend/.git research/.git frontend/.git
```
Expected: `test ! -e backend/.git && test ! -e research/.git && test ! -e frontend/.git` succeeds.

- [ ] **Step 7: Remove submodule config file**

Run:
```bash
rm -f .gitmodules
```
Expected: `.gitmodules` absent.

## Task 3: Update mise Tasks

**Files:**
- Modify: `mise.toml`

- [ ] **Step 1: Replace `mise.toml` with flat-path task registry**

Write `mise.toml` exactly:
```toml
[tools]
python = "3.13"
uv = "latest"
node = "25"
gh = "latest"
docker-compose = "latest"
rclone = "latest"

[env]
UV_PROJECT_ENVIRONMENT = "research/.venv"

[tasks.sync]
description = "Install research dependencies"
run = "uv --directory research sync"

[tasks.qdrant-up]
description = "Start local Qdrant"
run = "$(mise where docker-compose)/docker-cli-plugin-docker-compose -f research/docker-compose.yml up -d"

[tasks.qdrant-down]
description = "Stop local Qdrant"
run = "$(mise where docker-compose)/docker-cli-plugin-docker-compose -f research/docker-compose.yml down"

[tasks.threshold]
description = "Run threshold experiment prepare flow"
run = "uv --directory research run python src/prepare.py --experiment threshold"

[tasks.experiment-list]
description = "List available experiments"
run = "uv --directory research run python src/run.py --experiment-list"

[tasks.backend-sync]
description = "Install backend dependencies"
run = "uv --directory backend sync --all-groups"

[tasks.frontend-install]
description = "Install frontend dependencies"
run = "pnpm --dir frontend install"

[tasks.backend-lint]
description = "Run backend lint, typecheck, and tests"
run = "uv --directory backend run ruff check . && uv --directory backend run ruff format --check . && uv --directory backend run mypy src && uv --directory backend run pytest"

[tasks.frontend-lint]
description = "Run frontend lint and build checks"
run = "pnpm --dir frontend lint && pnpm --dir frontend typecheck && pnpm --dir frontend build"

[tasks.workspace-prepare]
description = "Prepare a MycoAI remote workspace"
run = "bash tools/workspace_bootstrap.sh prepare"

[tasks.workspace-smoke-check]
description = "Validate the MycoAI remote workspace"
run = "bash tools/workspace_bootstrap.sh smoke-check"

[tasks.workspace-recover]
description = "Recover a MycoAI remote workspace"
run = "bash tools/workspace_bootstrap.sh recover"

[tasks.project-init]
description = "Init full monorepo dependencies"
run = "mise install && uv --directory research sync && uv --directory backend sync --all-groups && pnpm --dir frontend install"

[tasks.dataset-sync-plan]
description = "Show dataset sync CLI help"
run = "uv run python tools/dataset_sync.py plan --help"

[tasks.dataset-sync-import]
description = "Show dataset import CLI help"
run = "uv run python tools/dataset_sync.py import --help"

[tasks.dataset-sync-export]
description = "Show dataset export CLI help"
run = "uv run python tools/dataset_sync.py export --help"

[tasks.install-spec-kit]
description = "Install the Specify CLI"
run = "uv tool install --force specify-cli --from git+https://github.com/github/spec-kit.git@v0.6.1"

[tasks.specify-check]
description = "Verify Spec Kit prerequisites"
run = "specify check"

[tasks.specify-init-opencode]
description = "Initialize Spec Kit for OpenCode"
run = "specify init --here --ai opencode --no-git --force"
```

- [ ] **Step 2: Verify mise parses tasks**

Run:
```bash
mise tasks
```
Expected: task list includes `project-init`, `backend-lint`, `frontend-lint`, `threshold` and no `submodules-checkout-branch`.

## Task 4: Rewrite Root Agent Instructions

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `CONTEXT.md`

- [ ] **Step 1: Replace old path refs in root instruction files**

Run:
```bash
python - <<'PY'
from pathlib import Path
repls = {
    'repos/fungal-cv-qdrant': 'research',
    'repos/mycoai_retrieval_backend': 'backend',
    'repos/mycoai_retrieval_frontend': 'frontend',
    'prototype': 'frontend',
}
for name in ['AGENTS.md', 'CLAUDE.md', 'CONTEXT.md', 'README.md']:
    p = Path(name)
    if not p.exists():
        continue
    text = p.read_text()
    for old, new in repls.items():
        text = text.replace(old, new)
    lines = [line for line in text.splitlines() if 'git submodule' not in line.lower() and 'submodule' not in line.lower()]
    p.write_text('\n'.join(lines) + '\n')
PY
```
Expected: files no longer contain old paths or submodule setup instructions.

- [ ] **Step 2: Verify root instructions have flat layout**

Run:
```bash
rg -n "repos/|git submodule|submodule|prototype" AGENTS.md CLAUDE.md CONTEXT.md README.md || true
```
Expected: no stale filesystem refs. Historical semantic mentions only if intentional.

## Task 5: Rewrite opencode Config And Rules

**Files:**
- Modify: `.opencode/agents/*.md`
- Modify: `.opencode/command/init.md`
- Modify: `.opencode/rules/*.md`
- Modify: `.opencode/skills/**/*.md` only if project-local paths appear

- [ ] **Step 1: Rewrite project-local opencode path refs**

Run:
```bash
python - <<'PY'
from pathlib import Path
root = Path('.opencode')
repls = {
    'repos/fungal-cv-qdrant': 'research',
    'repos/mycoai_retrieval_backend': 'backend',
    'repos/mycoai_retrieval_frontend': 'frontend',
    'prototype': 'frontend',
}
for p in root.rglob('*'):
    if not p.is_file() or 'node_modules' in p.parts:
        continue
    try:
        text = p.read_text()
    except UnicodeDecodeError:
        continue
    new = text
    for old, val in repls.items():
        new = new.replace(old, val)
    lines = []
    for line in new.splitlines():
        lower = line.lower()
        if 'git submodule update' in lower or 'submodule branch' in lower or 'align submodule' in lower:
            continue
        lines.append(line)
    if '\n'.join(lines) + '\n' != text:
        p.write_text('\n'.join(lines) + '\n')
PY
```
Expected: opencode config keeps files but uses flat paths.

- [ ] **Step 2: Verify opencode stale refs**

Run:
```bash
rg -n "repos/|git submodule|submodule|prototype" .opencode --glob '!node_modules/**' || true
```
Expected: no stale operational refs.

## Task 6: Rewrite Docs And Remove Stale Submodule Docs

**Files:**
- Modify/delete: `docs/**/*.md`
- Keep: `docs/` tree itself

- [ ] **Step 1: Rewrite docs paths**

Run:
```bash
python - <<'PY'
from pathlib import Path
repls = {
    'repos/fungal-cv-qdrant': 'research',
    'repos/mycoai_retrieval_backend': 'backend',
    'repos/mycoai_retrieval_frontend': 'frontend',
    'prototype': 'frontend',
}
for p in Path('docs').rglob('*.md'):
    text = p.read_text()
    new = text
    for old, val in repls.items():
        new = new.replace(old, val)
    lines = [line for line in new.splitlines() if 'git submodule' not in line.lower() and 'submodule' not in line.lower()]
    p.write_text('\n'.join(lines) + '\n')
PY
```
Expected: docs use flat paths.

- [ ] **Step 2: Remove docs whose core subject is submodule workflow**

Run:
```bash
python - <<'PY'
from pathlib import Path
for p in Path('docs').rglob('*.md'):
    text = p.read_text().lower()
    if text.count('submodule') >= 3 or 'git submodule update' in text:
        p.unlink()
PY
```
Expected: only docs dominated by submodule setup are deleted.

- [ ] **Step 3: Verify docs stale refs**

Run:
```bash
rg -n "repos/|git submodule|submodule|prototype" docs || true
```
Expected: no stale operational refs.

## Task 7: Rewrite Tools For Flat Layout

**Files:**
- Modify: `tools/workspace_bootstrap.sh`
- Modify: `tools/dataset_sync.py`
- Modify: any other `tools/**` file with old paths

- [ ] **Step 1: Rewrite tools paths**

Run:
```bash
python - <<'PY'
from pathlib import Path
repls = {
    'repos/fungal-cv-qdrant': 'research',
    'repos/mycoai_retrieval_backend': 'backend',
    'repos/mycoai_retrieval_frontend': 'frontend',
    'prototype': 'frontend',
}
for p in Path('tools').rglob('*'):
    if not p.is_file():
        continue
    try:
        text = p.read_text()
    except UnicodeDecodeError:
        continue
    new = text
    for old, val in repls.items():
        new = new.replace(old, val)
    lines = [line for line in new.splitlines() if 'git submodule update' not in line.lower()]
    p.write_text('\n'.join(lines) + '\n')
PY
```
Expected: tool scripts use `research`, `backend`, `frontend`.

- [ ] **Step 2: Verify shell syntax**

Run:
```bash
bash -n tools/workspace_bootstrap.sh
```
Expected: no output, exit code 0.

- [ ] **Step 3: Verify tools stale refs**

Run:
```bash
rg -n "repos/|git submodule|submodule|prototype" tools || true
```
Expected: no stale operational refs.

## Task 8: Global Stale Reference Sweep

**Files:**
- Modify all tracked text files with stale refs found by scan

- [ ] **Step 1: Scan repo excluding dependencies and git metadata**

Run:
```bash
rg -n "repos/fungal-cv-qdrant|repos/mycoai_retrieval_backend|repos/mycoai_retrieval_frontend|git submodule|submodule|prototype" --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' --glob '!backend/.venv/**' --glob '!research/.venv/**' --glob '!.git/**' || true
```
Expected: no stale refs except approved historical semantic mentions.

- [ ] **Step 2: Check no nested git dirs remain**

Run:
```bash
find frontend backend research -name .git -print
```
Expected: no output.

- [ ] **Step 3: Check git status shape**

Run:
```bash
git status --short
```
Expected: `.gitmodules` deleted, old submodule paths deleted, new `frontend/`, `backend/`, `research/` added, docs/config modified.

## Task 9: Dependency Install Validation

**Files:**
- No planned edits unless commands fail due path-only issues

- [ ] **Step 1: Run project init**

Run:
```bash
mise run project-init
```
Expected: research/backend/frontend dependencies install or report existing lockfile/env issues.

- [ ] **Step 2: Run research experiment list smoke**

Run:
```bash
mise run experiment-list
```
Expected: command lists available experiments.

## Task 10: Backend Validation

**Files:**
- No planned edits unless path migration breaks imports/config

- [ ] **Step 1: Run backend checks**

Run:
```bash
mise run backend-lint
```
Expected: `ruff check`, `ruff format --check`, `mypy`, and `pytest` pass.

- [ ] **Step 2: If backend check fails due old path text, fix exact file**

Run:
```bash
rg -n "repos/|prototype|fungal-cv-qdrant" backend || true
```
Expected: fix only path-related failures, then rerun `mise run backend-lint`.

## Task 11: Frontend Validation

**Files:**
- No planned edits unless path migration breaks Vite/package config

- [ ] **Step 1: Run frontend checks**

Run:
```bash
mise run frontend-lint
```
Expected: `pnpm --dir frontend lint`, `typecheck`, and `build` pass.

- [ ] **Step 2: If frontend check fails due old path text, fix exact file**

Run:
```bash
rg -n "repos/|prototype|mycoai_retrieval_frontend" frontend --glob '!node_modules/**' --glob '!dist/**' || true
```
Expected: fix path-related failures, then rerun `mise run frontend-lint`.

## Task 12: Research Validation

**Files:**
- No planned edits unless path migration breaks config/tests

- [ ] **Step 1: Run research tests**

Run:
```bash
uv --directory research run pytest tests/ -q
```
Expected: tests pass.

- [ ] **Step 2: Run research lint**

Run:
```bash
uv --directory research run python -m ruff check src/experiments/
```
Expected: lint passes.

- [ ] **Step 3: If research check fails due old path text, fix exact file**

Run:
```bash
rg -n "repos/|prototype|mycoai_retrieval" research || true
```
Expected: fix path-related failures, then rerun Step 1 and Step 2.

## Task 13: Final Verification And Handoff

**Files:**
- Inspect all changed files

- [ ] **Step 1: Run final stale reference sweep**

Run:
```bash
rg -n "repos/fungal-cv-qdrant|repos/mycoai_retrieval_backend|repos/mycoai_retrieval_frontend|git submodule|submodule|prototype" --glob '!frontend/node_modules/**' --glob '!frontend/dist/**' --glob '!backend/.venv/**' --glob '!research/.venv/**' --glob '!.git/**' || true
```
Expected: no stale operational refs.

- [ ] **Step 2: Run final git status**

Run:
```bash
git status --short --branch
```
Expected: reviewable flattened migration changes.

- [ ] **Step 3: Run final diff stats**

Run:
```bash
git diff --stat
```
Expected: confirms config/docs updates; new large directories may appear as untracked until staged.

- [ ] **Step 4: Report validation evidence**

Return concise summary:
```text
Layout: frontend/, backend/, research/ present; repos/ and .gitmodules removed.
Updated: mise.toml, docs, AGENTS/CLAUDE, .opencode, tools.
Validation: <commands and pass/fail outputs>.
Risks: <remaining failures if any>.
```

## Self-Review

- Spec coverage: all approved design requirements map to Tasks 2-13.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type/command consistency: flat paths are `frontend`, `backend`, `research` throughout.
- Commit steps intentionally omitted because user has not explicitly requested commits.
