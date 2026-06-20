# research_audit

## Objective

Inspect current dataset, Qdrant, weights, results, and prior reports before rerunning experiments under the leakage-safe protocol.

## Entry Point

```bash
uv --directory research run python -m src.experiments.research_audit.run
```

## Outputs

Artifacts under `results/research_audit/`:
- `inventory.json`
- `dataset_summary.csv`
- `qdrant_collections.json`
- `risk_flags.md`
- `reports_summary.json`
