# Contract: Agent Delegation Protocol

**Version**: 1.0.0
**Date**: 2026-05-05

## Agent Roles and Models

| Agent | Model | Mode | Permission Profile |
|-------|-------|------|--------------------|
| `autolab` | BigBrain | primary | read-only + delegate |
| `researcher` | BigBrain | agent | read + web fetch + write `research/` |
| `planner` | MidBrain | agent | read `research/` + write `research/results.tsv` status |
| `worker` | MiniBrain | agent | git worktree + edit in worktree + `uv run prepare.py` + CSV lock-append |
| `reporter` | MiniBrain | agent | read-only + trackio write + optional HF push |

## Delegation Flow

```
Scientist → autolab
  autolab → researcher  (optional: "research topic X")
  autolab → planner     ("queue hypotheses from paper-ideas.md")
    planner → worker    ("run hypothesis: <hypothesis>")
      worker → [git worktree] → [run_accuracy.py] → [prepare.py] → [CSV append]
    planner → reporter  (on completion: "summarize results")
  autolab ← reporter    (status summary)
Scientist ← autolab
```

## Hypothesis Handoff (Planner → Worker)

Planner passes to Worker agent session:

```markdown
## Hypothesis Assignment

- **experiment**: retrieval
- **run_id**: retrieval-20260505-abc123
- **output_root**: /home/dat/dev/mycoai/results/retrieval-20260505-abc123/
- **branch**: autoresearch/retrieval/3-cosine-top5
- **description**: "Use cosine similarity with top-5 retrieval instead of dot product"
- **strategy_source**: research/paper-ideas.md#3
```

Worker MUST:
1. Create worktree: `git -C repos/fungal-cv-qdrant worktree add .runtime/worktrees/<experiment-id> <branch>`
2. Modify `run_accuracy.py` in the worktree
3. Run: `uv run python src/prepare.py --experiment <name> --description "<description>"`
4. Lock-append result to `results/autoresearch/<experiment>.csv`
5. Report back: `ExperimentResult` fields

## Reporter Invocation

Reporter reads from:
- `results/autoresearch/{experiment}.csv` (staircase ledger)
- `research/results.tsv` (full run ledger)
- Active worktree list: `git -C repos/fungal-cv-qdrant worktree list`

Reporter emits:
```markdown
## Experiment Status

**Best F1**: 0.847 (experiment #12, strategy: cosine_top5_retrieval)
**Active workers**: 1 (branch: autoresearch/retrieval/3-cosine-top5)
**Completed this session**: 3 runs
**Staircase chart**: results/autoresearch/retrieval.png
**Trackio event**: logged (run_id: retrieval-20260505-abc123)
```

## Research Notebook Format

### paper-ideas.md entry

```markdown
## Paper: <Title>

- **URL**: <url>
- **Status**: pending
- **Methodology**: <one paragraph>
- **Fit Assessment**: <why this applies to fungal retrieval>
- **Proposed Strategy**: <strategy snippet for program.md or run_accuracy.py>
```

### do-not-repeat.md entry

```markdown
- `<strategy_name>` — tried in run_id `<run_id>`, F1=<score>, reason rejected: <why>
```
