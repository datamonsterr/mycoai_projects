# Contract: Experiment Run Interface

**Producer**: `repos/fungal-cv-qdrant/src/experiments/<name>/run.py`
**Consumer**: Worker agent (via `cli.py`); Planner (reads ExperimentResult from results.tsv)
**Version**: 1.0.0

## Python Interface

```python
from dataclasses import dataclass, field

@dataclass
class ExperimentParams:
    run_id: str
    output_root: str
    description: str

@dataclass
class ExperimentResult:
    f1_score: float
    strategy_name: str
    artifact_paths: list[str]
    run_id: str

def run(params: ExperimentParams) -> ExperimentResult:
    """
    Execute one experiment run.
    MUST:
    - Write all outputs under params.output_root/
    - NOT write to any global path outside output_root
    - Return ExperimentResult with all artifact_paths existing on disk
    - Be importable without side effects (no top-level I/O)
    """
```

## CLI Interface

```bash
uv run python -m src.experiments.<name>.cli \
  --run-id <run_id> \
  --output-root <path> \
  --description "<description>" \
  [--experiment-specific-args ...]
```

Exit codes: `0` success, `1` experiment failure (result logged), `2` config error.

## Output Root Convention

All file writes MUST be scoped under `output_root`:
```
<output_root>/
├── results.json          # ExperimentResult as JSON
├── log/
│   └── run.log
└── artifacts/
    └── ...               # experiment-specific outputs
```

`results.json` schema:
```json
{
  "f1_score": 0.847,
  "strategy_name": "cosine_top5_retrieval",
  "artifact_paths": ["/abs/path/results/<run_id>/artifacts/confusion.png"],
  "run_id": "retrieval-20260505-abc123"
}
```

## Shared Staircase CSV Append

After `run()` returns, Worker appends to `results/autoresearch/{experiment}.csv` at monorepo root using `fcntl.flock(fd, LOCK_EX)`. Format matches existing staircase chart reader:

```csv
experiment_index,f1_score,strategy_name,run_id,timestamp
```

Worker holds lock only during the single `csv.writer.writerow()` call.

## Invariants

1. `run()` MUST be idempotent with same `run_id` (re-running overwrites `output_root` contents only)
2. Two concurrent `run()` calls with different `run_id` values MUST NOT interfere
3. `run()` MUST NOT modify any file outside `output_root` except the shared CSV (via lock)
4. `ExperimentResult.f1_score` MUST match the value appended to the shared CSV
