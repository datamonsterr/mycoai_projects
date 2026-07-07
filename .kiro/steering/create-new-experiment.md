---
inclusion: manual
---

# Create New Experiment

## When to Use

When user asks to create, initialize, or scaffold a new experiment.

## Before Creating — Ask These Questions

1. **Experiment name?** (e.g., `segmentation`, `feature-extractor`)
2. **Independent variable?** (What changes between attempts?)
3. **Accuracy metric?** (F1? Retrieval accuracy? IoU?)
4. **Which existing components?** (KNN retrieval, feature extraction, preprocessing?)
5. **Branch name?** (auto-generated from name if not specified)
6. **Ready to start or exploratory?**
7. **Environment strategy?** (`E1` = same medium, `E2` = all media)
8. **Aggregation strategy?** (`weighted` or `uni`)
9. **K value?** (default 11)
10. **Use shared cross-validation library?** (most retrieval experiments should)

## What to Create

1. `src/experiments/<name>/program.md`
2. `src/experiments/<name>/run_accuracy.py`
3. Entry in `EXPERIMENT_REGISTRY` in `src/run.py`
4. Git branch: `autoresearch/{name}/1-initial-baseline`

## Run Commands

```bash
# Run experiment
uv run python src/run.py --experiment {name} --description "change description"

# Prepare with checks
uv run python src/prepare.py --experiment {name}
```

## File Checklist

- [ ] `src/experiments/{name}/program.md`
- [ ] `src/experiments/{name}/run_accuracy.py`
- [ ] Entry in `EXPERIMENT_REGISTRY` in `src/run.py`
- [ ] Git branch created
