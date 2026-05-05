# Data Model: Autolab Multi-Agent System

**Phase 1 output for**: `004-autolab-multi-agent`
**Date**: 2026-05-05

## Entities

### 1. ExperimentParams

Location: `repos/fungal-cv-qdrant/src/experiments/<name>/run.py`

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `run_id` | `str` | Unique identifier for this run, e.g. `retrieval-20260505-abc123` | Non-empty, filesystem-safe (no `/`, spaces) |
| `output_root` | `str` | Absolute path for all output artifacts, e.g. `/monorepo/results/<run_id>/` | Must be writable; created if absent |
| `description` | `str` | Human-readable strategy description passed to log | Non-empty |

Experiment-specific subclasses add additional fields (e.g. `threshold`, `n_clusters`).

---

### 2. ExperimentResult

Location: `repos/fungal-cv-qdrant/src/experiments/<name>/run.py`

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `f1_score` | `float` | Macro F1 on validation set | 0.0–1.0 |
| `strategy_name` | `str` | Short label identifying the strategy variant | Non-empty, ≤30 chars |
| `artifact_paths` | `list[str]` | Absolute paths of produced artifacts (charts, logs, model files) | All paths must exist after `run()` returns |
| `run_id` | `str` | Echo of input `run_id` for traceability | Matches `ExperimentParams.run_id` |

---

### 3. Hypothesis

Location: `repos/fungal-cv-qdrant/research/paper-ideas.md` (markdown table row)

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Paper title or heuristic label |
| `url` | `str` | Paper URL or `heuristic` |
| `methodology` | `str` | One-paragraph extracted methodology |
| `fit_assessment` | `str` | Why this applies to fungal retrieval |
| `status` | `enum` | `pending` / `in-progress` / `completed` / `rejected` |
| `proposed_strategy` | `str` | `program.md`-style strategy snippet |

State transitions:
```
pending → in-progress  (Planner assigns to Worker)
in-progress → completed (Worker records result)
in-progress → rejected  (Worker fails; Planner marks rejected)
pending → rejected      (Planner deduplication check)
```

---

### 4. RunRecord

Location: `repos/fungal-cv-qdrant/research/results.tsv` (append-only TSV)

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | `str` | ISO-8601 UTC, e.g. `2026-05-05T14:23:00Z` |
| `experiment` | `str` | Experiment name, e.g. `retrieval` |
| `run_id` | `str` | Unique run identifier |
| `strategy` | `str` | Strategy label |
| `f1_score` | `float` | F1 score from ExperimentResult |
| `is_new_best` | `bool` | `true` if this run beat prior best |
| `worker_branch` | `str` | Git branch used by Worker, e.g. `autoresearch/retrieval/3-triplet-loss` |

---

### 5. WorkerWorktree

Ephemeral filesystem entity, not persisted. Lifecycle:

```
created     → git worktree add .runtime/worktrees/<experiment-id> <branch>
active      → Worker modifies run_accuracy.py, runs prepare.py
completed   → ExperimentResult recorded; worktree removed (unless new best)
retained    → new best: worktree kept until merged to autoresearch/<experiment>
```

Naming: `<experiment-id>` = `<experiment-name>-<run_id>` e.g. `retrieval-20260505-abc123`

---

### 6. ResearchPaper

Location: `repos/fungal-cv-qdrant/research/papers/<slug>.md` (markitdown output)

| Field | Type | Description |
|-------|------|-------------|
| `slug` | `str` | URL-safe lowercase filename, e.g. `attention-is-all-you-need` |
| `source_url` | `str` | Original paper URL |
| `downloaded_at` | `str` | ISO-8601 timestamp |
| `content` | `str` | Full markdown from markitdown conversion |

Each paper file corresponds to exactly one entry in `research/paper-ideas.md`.

---

## File Layout Summary

```
repos/fungal-cv-qdrant/
├── research/
│   ├── paper-ideas.md       # markdown table of Hypothesis entities
│   ├── results.tsv          # append-only RunRecord TSV
│   ├── do-not-repeat.md     # markdown list of rejected/completed hypotheses
│   └── papers/
│       └── <slug>.md        # ResearchPaper content
├── .runtime/
│   └── worktrees/
│       └── <experiment-id>/ # ephemeral WorkerWorktree
└── src/experiments/
    ├── retrieval/
    │   ├── run.py           # ExperimentParams + ExperimentResult + run()
    │   └── cli.py           # argparse wrapper
    └── threshold/
        ├── run.py
        └── cli.py

results/                     # monorepo root
├── autoresearch/
│   ├── retrieval.csv        # shared staircase ledger (file-locked writes)
│   └── retrieval.png        # staircase chart
└── <run_id>/                # per-Worker isolated output root
    └── ...
```
