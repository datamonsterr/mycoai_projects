# Quickstart: Autolab Multi-Agent System

**For**: `004-autolab-multi-agent`
**Date**: 2026-05-05

## Prerequisites

```bash
# Monorepo root
mise install
uv --directory repos/fungal-cv-qdrant sync

# Verify git worktree available
git worktree list
```

## One-Command Autolab Session

```bash
# From monorepo root, launch opencode with autolab agent
opencode
# Then prompt: "run one autoresearch pass on retrieval experiment"
```

## Running Individual Agents

### Researcher — find papers

Invoke `researcher` agent with:
```
research top techniques for fungal species retrieval using feature embeddings
```
Output: `repos/fungal-cv-qdrant/research/paper-ideas.md` updated; PDFs at `repos/fungal-cv-qdrant/research/papers/`.

### Planner — queue hypotheses

Invoke `planner` agent with:
```
queue all pending hypotheses from research/paper-ideas.md, assign to workers
```
Output: `repos/fungal-cv-qdrant/research/results.tsv` updated with in-progress entries.

### Worker — run one experiment

Invoke `worker` agent with a hypothesis assignment block (see `contracts/agent-delegation-contract.md`). Worker creates its own worktree and cleans up on exit.

### Reporter — check status

Invoke `reporter` agent with:
```
summarize current experiment status
```
Output: status block + staircase chart path + optional Trackio event.

## New Experiment Package CLI

After restructure, invoke any experiment directly:

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.retrieval.cli \
  --run-id test-001 \
  --output-root /tmp/test-001 \
  --description "baseline smoke test"
```

## Research Notebook Layout

```
repos/fungal-cv-qdrant/research/
├── paper-ideas.md       # add hypotheses here
├── results.tsv          # auto-appended by Worker
├── do-not-repeat.md     # auto-updated by Planner
└── papers/              # auto-populated by Researcher
```

## Concurrent Worker Safety

Workers are safe to run in parallel. Each Worker:
- Uses its own `run_id` → isolated `results/<run_id>/` output directory
- Uses `fcntl.flock` for shared CSV append
- Operates in its own git worktree

Max concurrent workers: `MAX_CONCURRENT_WORKERS=2` (default). Override per session.

## Verification

```bash
# Run tests
uv --directory repos/fungal-cv-qdrant run pytest tests/

# Lint restructured experiments
uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/

# Type-check priority packages
uv --directory repos/fungal-cv-qdrant run mypy src/experiments/retrieval/ src/experiments/threshold/

# Smoke test concurrent isolation
# Run two worker agents with different run_ids, verify non-overlapping output under results/
```
