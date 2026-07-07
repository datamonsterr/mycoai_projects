---
inclusion: fileMatch
fileMatchPattern: "**/src/experiments/**"
---

# Branch Naming: Autoresearch Experiments

## Branch Format

All experiment branches MUST follow:

```
autoresearch/{experiment-name}/{N}-{summary}
```

| Component | Meaning |
|-----------|---------|
| `autoresearch/` | Prefix for experiment branches |
| `{experiment-name}` | Short identifier (lowercase, hyphenated, max 3 words) |
| `{N}` | Sequential attempt number (1, 2, 3...) |
| `{summary}` | Kebab-case description of the change (max 5 words) |

## Examples

```
autoresearch/segmentation/1-kmeans-baseline
autoresearch/feature-extractor/2-add-yolo-segmentation
autoresearch/embedding-lr/1-triplet-loss-baseline
```

## Merging Best Results

1. Merge the winning branch to `autoresearch/{experiment-name}` (no attempt suffix)
2. The `{experiment-name}` branch always holds the best known result
3. Discarded attempts remain as historical record — never merged

## Creating a New Experiment

```bash
git checkout -b autoresearch/my-experiment/1-initial-baseline
```

Then implement in `src/experiments/<name>/`.
