# Implementation Plan: Autolab Multi-Agent System

**Branch**: `004-autolab-multi-agent` | **Date**: 2026-05-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-autolab-multi-agent/spec.md`

## Summary

Build a 5-agent multi-agent orchestration layer (Autolab, Researcher, Planner, Worker, Reporter) on top of the existing `fungal-cv-qdrant` autoresearch infrastructure. Restructure 9 experiment packages to expose a uniform `run(params) -> ExperimentResult` contract enabling safe parallel Worker execution via git worktrees. Agent definitions live in monorepo `.opencode/agents/`; research notebook lives in `repos/fungal-cv-qdrant/research/`; isolated worktrees live in `repos/fungal-cv-qdrant/.runtime/worktrees/`. Reference design adapted from `burtenshaw/multiautoresearch` pre-training layout.

## Technical Context

**Language/Version**: Python 3.13 (matches monorepo `uv` lockfile)
**Primary Dependencies**: `uv`, `git worktree`, `markitdown` (via `uvx`), `trackio`, `hf` CLI (optional); existing `fungal-cv-qdrant` stack (OpenCV, NumPy, pandas, scikit-learn)
**Package / Command Tooling**: `uv`/`uvx` for all Python; `gh` for GitHub automation; `pnpm` not touched
**Storage**: append-only `results/autoresearch/{experiment}.csv` at monorepo root; `research/results.tsv`, `research/paper-ideas.md`, `research/do-not-repeat.md` inside `repos/fungal-cv-qdrant/`; per-run output under `results/<run_id>/` at monorepo root
**Testing**: `pytest` via `uv --directory repos/fungal-cv-qdrant`; `ruff check`; `mypy` on restructured experiment packages
**Target Platform**: Linux (local workstation + Vast.ai GPU)
**Project Type**: Agent orchestration layer + Python library restructure
**Performance Goals**: ≥2 concurrent Worker agents without output corruption; experiment `run()` latency unchanged from baseline
**Constraints**: `prepare.py` immutable; `MAX_CONCURRENT_WORKERS` default 2; worktrees must not bleed into main checkout
**Scale/Scope**: 5 agent files; 9 experiment packages restructured (2 priority, 7 follow-up); 3 research notebook files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: agent files → monorepo `.opencode/agents/`; experiment packages → `repos/fungal-cv-qdrant/src/experiments/`; research notebook → `repos/fungal-cv-qdrant/research/`; shared runtime artifacts → monorepo root `results/`, `weights/`, `Dataset/`
- [x] Traceability is explicit: `retrieval` and `threshold` packages produce F1 artifacts consumed by backend/frontend via validated CSV and payload schemas; no new backend/frontend dependency introduced here
- [x] Reimplementation is explicit: this feature modifies only `fungal-cv-qdrant` experiment infrastructure and monorepo agent config; backend/frontend MUST NOT import from these paths
- [x] Canonical toolchains are explicit: all Python via `uv`/`uvx`; GitHub automation via `gh`; no `pip`/`npm` introduced
- [x] Validation is explicit:
  - `uv --directory repos/fungal-cv-qdrant run pytest tests/`
  - `uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/`
  - `uv --directory repos/fungal-cv-qdrant run mypy src/experiments/retrieval/ src/experiments/threshold/`
  - Concurrent Worker smoke test with two distinct `run_id` values
- [x] Definition of done is explicit: named in spec §Definition of Done — pytest, ruff, mypy pass; concurrent output isolation verified; manual Autolab end-to-end loop completed; PR evidence includes log + F1 comparison table + staircase screenshot
- [x] Contract sync is explicit: `AGENTS.md` updated with new agent names and models; `.opencode/agents/` new files; `repos/fungal-cv-qdrant/research/` layout documented in quickstart.md
- [x] Minimality is justified: new shared schema limited to `ExperimentResult` typed dict + `ExperimentParams` typed dict; no new compatibility layers; `.runtime/worktrees/` gitignored; cross-repo coupling is zero (agent config in monorepo root, not in submodule)

## Project Structure

### Documentation (this feature)

```text
specs/004-autolab-multi-agent/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── experiment-run-contract.md
│   └── agent-delegation-contract.md
└── tasks.md             # Phase 2 output (speckit.tasks)
```

### Source Code (affected paths)

```text
.opencode/agents/
├── autolab.md           # NEW — primary agent (BigBrain)
├── researcher.md        # NEW — literature scout (BigBrain)
├── planner.md           # NEW — queue coordinator (MidBrain)
├── worker.md            # NEW — derived from autoresearch.md (MiniBrain)
├── reporter.md          # NEW — observer/summarizer (MiniBrain)
└── autoresearch.md      # MODIFIED — baseline kept, worker derives from it

repos/fungal-cv-qdrant/
├── src/experiments/
│   ├── retrieval/       # RESTRUCTURED (priority 1)
│   │   ├── __init__.py
│   │   ├── run.py       # exposes run(params) -> ExperimentResult
│   │   └── cli.py       # wraps run() for uv run invocation
│   ├── threshold/       # RESTRUCTURED (priority 1)
│   │   ├── __init__.py
│   │   ├── run.py
│   │   └── cli.py
│   └── [7 remaining]    # follow-up pass
├── research/
│   ├── paper-ideas.md   # NEW — canonical hypothesis list
│   ├── results.tsv      # NEW — append-only run ledger
│   ├── do-not-repeat.md # NEW — tried-and-failed hypotheses
│   └── papers/          # NEW — markitdown-converted PDFs
├── .runtime/
│   └── worktrees/       # NEW — per-hypothesis isolated worktrees (gitignored)
└── .gitignore           # MODIFIED — add .runtime/worktrees/

results/autoresearch/    # monorepo root — unchanged layout
Dataset/                 # monorepo root — unchanged
weights/                 # monorepo root — unchanged
```

### Affected Repositories

| Repo Path | Type | Reason |
|-----------|------|--------|
| repos/fungal-cv-qdrant | submodule | Primary target: experiment restructure + research notebook + worktree runtime |
| . (monorepo root) | root | New agent files in `.opencode/agents/`; AGENTS.md update |

## OpenCode Extension Layer

### Agent Configuration (`.opencode/opencode.json`)

Based on OpenCode docs (May 2026), agents support: `mode` (primary/subagent/all), `model`, `temperature`, `steps`, `permission` (fine-grained bash globs), `task` permission (which subagents each agent can invoke), `hidden` (internal agents invisible to `@` autocomplete), `color`.

**Model tiers applied**:

| Agent | Model | Mode | Rationale |
|-------|-------|------|-----------|
| `autolab` | `9router/BigBrain` | primary | Open-ended orchestration; multi-step planning |
| `researcher` | `9router/BigBrain` | subagent | Deep reasoning for paper synthesis and fit validation |
| `planner` | `9router/MidBrain` | subagent | Structured queue management; no open-ended generation |
| `worker` | `9router/MiniBrain` | subagent | Mechanical fixed loop; determinism over reasoning |
| `reporter` | `9router/MiniBrain` | subagent | Read-only summary; no reasoning required |
| `superagent` | `9router/BigBrain` | primary | Upgraded from MiniMax for delivery quality |
| `prepare`, `test-writer`, `manual-browser-tester`, `e2e-writer`, `create-new-pr`, `write-report`, `vast-ai-runner`, `vast-ai-setup` | `9router/MidBrain` | subagent | Moderate tasks with structured outputs |
| `test-runner`, `diagram-renderer`, `sync-data`, `autoresearch` | `9router/MiniBrain` | subagent | Mechanical execution, minimal judgment |

### Custom Tools (`.opencode/tools/`)

Existing tools: `experiment-log.ts`, `create-new-worktree.ts`, `latex-compile.ts`, `mermaid-render.ts`

**New tools added**:

| Tool | File | Purpose |
|------|------|---------|
| `hypothesis-validator` | `hypothesis-validator.ts` | Check strategy against `paper-ideas.md` + `do-not-repeat.md` before Worker is spawned. Returns `VALID`, `DUPLICATE`, or `REJECTED`. Prevents wasted GPU time on already-tried ideas. |
| `experiment-test-runner` | `experiment-test-runner.ts` | Run `ruff`, `mypy`, `import`, and `pytest` checks on restructured experiment packages. Worker and Planner use this to gate deployment of restructured packages. |

**Additional tools to consider** (not yet implemented):

| Tool | Purpose | When to build |
|------|---------|---------------|
| `research-queue-status` | Read `paper-ideas.md` + `results.tsv` and return a compact queue table (pending/in-progress/completed counts per experiment) | Build when Planner needs programmatic queue visibility |
| `worktree-cleanup` | List all worktrees, identify completed (non-best) ones, batch-remove safely | Build when worktree accumulation becomes a pain point |
| `csv-staircase-append` | Lock-safe CSV append with `fcntl` in TypeScript for Worker — avoids inline Python snippets | Build during Worker implementation to keep append logic out of agent prompts |
| `hf-paper-search` | Call Hugging Face papers API to find relevant papers by topic keyword — gives Researcher a structured entrypoint without needing websearch for every paper | Build when Researcher needs faster paper discovery |

### Plugins (`.opencode/plugins/`)

**New plugin added**:

| Plugin | File | Purpose |
|--------|------|---------|
| `AutolabCompactionPlugin` | `autolab-compaction.ts` | Injects Autolab session state (last 5 TSV rows, pending/in-progress queue counts, active worktrees) into the compaction context. Prevents context compaction from losing experiment state in long multi-agent sessions. |

**Additional plugins to consider**:

| Plugin | Purpose | When to build |
|--------|---------|---------------|
| `session-idle-notifier` | Send desktop notification (via `notify-send` on Linux) when Autolab becomes idle — useful for long experiment runs where scientist walks away | Build when running overnight experiment loops |
| `env-guard` | Prevent any agent from reading `.env` files (security best practice from docs) | Build if secrets management becomes a concern |
| `worker-concurrency-guard` | `tool.execute.before` hook on `bash` — intercept `git worktree add` calls, count active worktrees, block if >MAX_CONCURRENT_WORKERS | Build as hard enforcement vs soft instruction in Worker prompt |

### Additional Subagents to Consider

| Agent | Model | Mode | Purpose |
|-------|-------|------|---------|
| `idea-validator` | MidBrain | subagent | Hidden internal agent invoked by Planner before adding to queue. Reads `do-not-repeat.md`, `paper-ideas.md`, and existing branch list. Returns `VALID/DUPLICATE/REJECT`. Replaces the `hypothesis-validator` custom tool approach for richer reasoning. |
| `memory-keeper` | MidBrain | subagent | Write-only access to `research/` markdown files. Planner and Reporter delegate all markdown writes here — keeps the boundary clean and prevents concurrent write conflicts on notebook files. Inspired by `burtenshaw/multiautoresearch` memory-keeper role. |
| `worktree-janitor` | MiniBrain | subagent | Invoked by Autolab after each loop iteration. Lists worktrees, identifies stale/failed ones (older than N minutes, no active Worker session), removes them. Keeps `.runtime/worktrees/` clean automatically. |

### Task Permission Topology

```
autolab (primary)
  ├── can invoke: researcher, planner, worker, reporter, memory-keeper, worktree-janitor
  └── cannot invoke: superagent, autoresearch (separate primary agents)

planner (subagent)
  ├── can invoke: memory-keeper, idea-validator
  └── cannot invoke: worker, researcher (must go via autolab)

worker (subagent)
  ├── can invoke: experiment-log tool, hypothesis-validator tool, experiment-test-runner tool
  └── cannot invoke: any other subagent (isolated by design)

reporter (subagent)
  └── cannot invoke: any subagent (read-only observer)
```

Configure via `permission.task` in agent frontmatter:
```yaml
permission:
  task:
    "*": deny
    "memory-keeper": allow
    "idea-validator": allow
```

## Complexity Tracking

No constitution violations requiring justification. Shared `ExperimentResult` schema is minimal (4 fields) and stays internal to `fungal-cv-qdrant`; no cross-repo coupling added.

Plugin and custom tool layer adds TypeScript/JS files to `.opencode/` only — does not affect Python experiment code or cross-repo boundaries.
