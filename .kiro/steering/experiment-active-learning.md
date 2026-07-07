---
inclusion: fileMatch
fileMatchPattern: "**/src/experiments/**"
---

# Experiment Active Learning — Log, Read, Improve

## Core Principle

Do NOT write a large procedural script that tries everything at once. Instead:
- Write SMALL, focused experiment files (< 10 lines each for strategy/result)
- Log every run to a shared structured log
- After each run, READ the log to understand what has been tried
- Use the log to decide what to try next (not re-run what already failed)

## Log Structure

```
results/{experiment}/log/
  experiments.log         <- one line per attempt
  attempt_001.json        <- full dict of all strategy F1s
  best_strategy.json      <- always current best
  all_experiments.csv     <- every individual experiment
  setup.json              <- shared config
  strategies/             <- individual strategy files tried
```

## Workflow Per Run

1. **Before running**: Read `best_strategy.json` and `experiments.log`
2. **Agent specifies experiment name**: meaningful description, not auto-generated
3. **Run**: execute the experiment
4. **After running**: update `best_strategy.json` if new best; append to log
5. **Read the log before next run** to avoid repeating failed strategies

## Threshold Experiment Algorithms (only these 3)

| Algorithm | Description |
|-----------|-------------|
| `f1_grid` | Sweep 500 thresholds, pick argmax F1 |
| `roc_opt` | Maximise Youden's J (sensitivity + specificity - 1) |
| `otsu` | Minimise intra-class variance |

Do NOT use `fpr_5pct` or `fpr_10pct` — they perform poorly.

## Formula Naming Conventions

| Prefix | Meaning |
|--------|---------|
| `s{i}` | Raw score of i-th neighbour |
| `gap_{i}_{j}` | s{i} - s{j} |
| `gnorm_{i}_{j}` | (s{i} - s{j}) / (s{i} + s{j}) |
| `ratio_{i}_{j}` | s{i} / s{j} |
| `avg_top{k}` | Mean of top-k scores |
| `gm_top{k}` | Geometric mean of top-k |

## Do NOT

- Run 1000 experiments in a single script without logging each one
- Overwrite previous results without reading the log first
- Auto-generate experiment names
- Create a new strategy file longer than 10 lines
