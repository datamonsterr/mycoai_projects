# Research: Autolab Multi-Agent System

**Phase 0 output for**: `004-autolab-multi-agent`
**Date**: 2026-05-05

## Summary

All unknowns resolved. No external unknowns remain; decisions below are grounded in existing codebase conventions and the `burtenshaw/multiautoresearch` reference layout.

---

## Decision 1: Agent Model Assignment

**Decision**: 
- `autolab` (primary orchestrator): **BigBrain** — handles natural-language planning, tool delegation, and end-to-end session ownership
- `researcher` (literature scout): **BigBrain** — requires deep reasoning to extract methodology from papers and assess fit against dataset/experiments
- `planner` (queue coordinator): **MidBrain** — queue management and status tracking; structured but not reasoning-heavy
- `worker` (experiment runner): **MiniBrain** — executes a fixed mechanical loop (git worktree → modify run_accuracy.py → prepare.py → log); determinism over reasoning
- `reporter` (observer): **MiniBrain** — reads logs and emits summaries; no novel reasoning required

**Rationale**: Assign strongest model where open-ended judgment is needed (Researcher, Autolab); save tokens with lighter models for mechanical roles (Worker, Reporter). Planner sits between: it needs to read structured files and make queue decisions without open-ended generation.

**Alternatives considered**: All BigBrain — rejected, excessive cost for mechanical agents. All MiniBrain — rejected, Researcher and Autolab need multi-step planning ability.

---

## Decision 2: Worktree Location and Lifecycle

**Decision**: Worktrees created at `repos/fungal-cv-qdrant/.runtime/worktrees/<experiment-id>/` via `git worktree add`. `.runtime/` added to `.gitignore` in `repos/fungal-cv-qdrant/`. Cleanup after outcome recorded unless new best (retained for merge). Script `opencode_worker.py` in reference repo replaced by Worker agent instructions inline.

**Rationale**: Mirrors `burtenshaw/multiautoresearch` pre-training layout exactly (`.runtime/worktrees/`). Keeps worktrees inside the submodule git graph for correct branch namespacing.

**Alternatives considered**: Monorepo root `.runtime/` — rejected, worktrees need to belong to the `fungal-cv-qdrant` git repo not the monorepo. Temp dirs — rejected, no branch tracking.

---

## Decision 3: Experiment Package Contract Design

**Decision**: Each restructured package exposes:
```python
# src/experiments/<name>/run.py
from dataclasses import dataclass

@dataclass
class ExperimentParams:
    run_id: str
    output_root: str  # absolute path, e.g. results/<run_id>/
    description: str
    # experiment-specific params follow

@dataclass
class ExperimentResult:
    f1_score: float
    strategy_name: str
    artifact_paths: list[str]
    run_id: str

def run(params: ExperimentParams) -> ExperimentResult: ...
```
`cli.py` wraps `run()` with `argparse` for `uv run python -m src.experiments.<name>.cli` invocation. Existing `prepare.py` continues to call the old interface; `cli.py` is the new parallel entrypoint for Worker agent use.

**Rationale**: `prepare.py` immutability is a hard constraint (Constitution §II). New `cli.py` + `run()` adds capability without modifying the existing invocation path. `dataclass` over `TypedDict` for runtime validation clarity. `output_root` injection ensures no global path writes.

**Alternatives considered**: Modify `prepare.py` — rejected, violates Constitution §II. Protocol/ABC — overkill for 9 packages, dataclass is sufficient. Pydantic models — not currently in `fungal-cv-qdrant` dependencies; avoid adding for this scope.

---

## Decision 4: Research Notebook Layout

**Decision**: Adopt `burtenshaw/multiautoresearch` notebook layout directly:
- `research/paper-ideas.md` — structured hypothesis list (paper title, URL, methodology, fit assessment, status, proposed strategy)
- `research/results.tsv` — append-only ledger: `timestamp`, `experiment`, `run_id`, `strategy`, `f1_score`, `is_new_best`, `worker_branch`
- `research/do-not-repeat.md` — tried-and-failed list
- `research/papers/<slug>.md` — markitdown-converted papers

**Rationale**: Direct match to reference repo avoids reinventing conventions. TSV chosen over CSV for `results` to avoid ambiguity with commas in strategy names. Paper storage in `research/papers/` keeps converted markdown near the ideas that reference them.

**Alternatives considered**: Single JSON queue file — rejected, not human-readable or diff-friendly. SQLite — overkill for ≤100 experiments per session.

---

## Decision 5: Concurrent Write Safety

**Decision**: Worker agents append to `results/autoresearch/{experiment}.csv` (monorepo root) using file lock via `fcntl.flock` on Linux. Each Worker also writes to its isolated `results/<run_id>/` directory which requires no locking.

**Rationale**: `fcntl.flock` is available on Linux (Vast.ai and local) without additional dependencies. `MAX_CONCURRENT_WORKERS=2` keeps contention negligible; lock acquisition is brief (one CSV row append).

**Alternatives considered**: Atomic rename pattern — more complex, not needed at this scale. Separate per-worker CSV files merged at end — breaks existing staircase chart reader which expects one shared CSV.

---

## Decision 6: Agent Permission Model

**Decision**:
- `autolab`: read-only + can delegate to other agents + can call `opencode_worker` create/run scripts
- `researcher`: read + web fetch + markitdown write to `research/papers/` and `research/paper-ideas.md`
- `planner`: read `research/paper-ideas.md` + write `research/results.tsv` status updates + no code edit
- `worker`: git worktree create/delete + edit `run_accuracy.py` in worktree + `uv run python src/prepare.py` + append to shared CSV with lock
- `reporter`: read-only + trackio write + optional HF Hub push

**Rationale**: Principle of least privilege. Planner must not edit code; Reporter must not modify experiment state. Worker is the only code-mutating agent and only in its worktree. Matches `burtenshaw/multiautoresearch` memory-keeper / experiment-worker separation.

**Alternatives considered**: All agents with full edit permission — rejected, violates isolation property and makes concurrent safety impossible to reason about.
