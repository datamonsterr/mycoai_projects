# Retrieval Experiment Program

## Objective

Consolidate retrieval evaluation, comprehensive benchmark runs, and ensemble-model analysis under a single experiment package.

## Entrypoint

```bash
uv run python -m src.experiments.retrieval.run <command> [options]
```

## Aggregation Strategies

All strategies produce per-species scores in **[0, 1]** and sort descending.

| Strategy | Formula | Range behaviour |
|---|---|---|
| `weighted` (default) | `scores[X] / total_known_neighbors` | Diluted by similar species; rarely >0.5 |
| `uni` | `count[X] / total_known_neighbors` | Ignores similarity magnitude |
| **`relative`** (recommended) | `scores[X] / Σ scores[all]` | Fraction of total evidence; top→1.0 when dominant; scores sum to 1 |
| `per_species_avg` | `scores[X] / count[X]` | Mean cosine similarity; natural 0–1 |
| `max_score` | `max(neighbor.score for X)` | Single best match; ignores prevalence |
| `perquery_avg` | Per-query `sum/K`, then mean across queries | Equivalent to weighted in clean data; worse with unknowns |
| `perquery_norm_avg` | Per-query normalize→sum=1, then mean | Equal voter per query; natural 0–1 |

**Recommendation**: Use `relative` for retrieval ranking — it scores each
species by its share of total evidence, so the top species naturally
approaches 1.0 when it dominates the neighbor pool.

## Commands

### 1) Comprehensive Retrieval Benchmark

Runs combinations of feature extractors, environment strategies, and aggregation strategies.

```bash
uv run python -m src.experiments.retrieval.run comprehensive \
  --identifier run_001 \
  --extractors resnet50 mobilenetv2 efficientnetv2 hog gabor colorhistogram \
  --env_strategies E1 E2 \
  --agg_strategies weighted uni relative per_species_avg max_score perquery_norm_avg \
  --k 5
```

### 2) Ensemble Analysis

Consumes comprehensive outputs and builds ensemble performance reports.

```bash
uv run python -m src.experiments.retrieval.run ensemble-analysis
```

### 3) Ensemble Report Rendering

Creates detailed charts for one strategy.

```bash
uv run python -m src.experiments.retrieval.run ensemble-report --strategy weighted
```

### 4) Strategy Comparison

Compares weighted and simple-average ensemble predictions.

```bash
uv run python -m src.experiments.retrieval.run ensemble-compare
```

## Outputs

- Retrieval metrics and per-strategy artifacts under `results/<identifier>/...`
- Ensemble artifacts under `results/ensemble_analysis/`
- CSV/ranked predictions and confusion matrices per run
