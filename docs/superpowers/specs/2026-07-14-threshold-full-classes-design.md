# 2026-07-14 Threshold Full-Classes Rerun Design

## Goal

Rerun the threshold experiment as a grouped-query-set evaluation instead of a per-segment binary screen, using the original-only Qdrant retrieval collection (original prepared + YOLO + EfficientNetB1 fine-tuned) as the searchable database and treating `Dataset/new_data_prepared` plus held-out known test queries as the evaluation set.

The run must produce final artifacts under `results/threshold_full_classes/`, including reproducible metrics, experiment logs, and analysis outputs.

## Why this change

The current threshold path mixes per-segment samples from known and incoming data, which creates two distortions:

1. known test queries are effectively oversampled because the six-query known protocol is later flattened into many rows
2. incoming data contributes repeated same-environment rows, which biases threshold fitting and weakens comparability

A grouped-query-set unit fixes both issues by scoring one decision per query set, not one decision per raw segment.

## Evaluation unit

### Known queries

Known queries follow the existing six-set retrieval protocol used in the retrieval experiments:

- 3 segment indices × 2 camera angles
- one grouped query set per `(segment_index, angle)` combination
- each grouped query set may include multiple media for the same held-out strain

A known grouped query counts as correct only if the final accepted species matches the ground-truth species.

### Unknown queries

Unknown queries come from `Dataset/new_data_prepared` and are grouped into analogous query sets so that repeated same-environment rows are collapsed into one decision unit.

The grouping rule should preserve the current threshold intent: aggregate multiple segment observations into one retrieval decision before thresholding.

## Objective metric

Use normal F1 score on grouped full-class decisions.

Define the threshold decision outcomes as:

- TP: known grouped query predicted as the correct known species
- FN: known grouped query predicted as the wrong species or `unknown`
- FP: unknown grouped query predicted as any known species
- TN: unknown grouped query predicted as `unknown`

This keeps threshold optimization binary at the acceptance layer while still requiring correct species identity for known-query success.

## Retrieval pipeline

### Search database

- Qdrant collection: original-only retrieval collection near `original_prepared_yolo_effb1ft`
- no incoming `new_data_prepared` items inserted into the collection
- held-out known strains remain excluded from neighbors when required by the evaluation split

### Query features

Before retrieval, extract YOLO-segment EfficientNetB1 fine-tuned features for all query segments once and save them to a JSON cache.

Cache requirements:

- stored under `results/threshold_full_classes/`
- contains enough metadata to rebuild grouped query sets without re-extraction
- supports resumable retrieval runs

### Grouped retrieval

For each grouped query set:

1. load cached segment features
2. query Qdrant per segment with the environment filter strategy required by the experiment
3. merge returned neighbors across all member segments
4. apply one group aggregator to form the ranked species list
5. apply one threshold formula to the ranked species scores
6. emit one grouped-query result row

## Search space

### Must search

- threshold formulas (existing + new candidates)
- threshold-selection algorithms already used by the threshold experiment
- grouped-query aggregators when practical

### Recommended grouped aggregators

Start with the smallest useful set:

1. weighted species-score sum across all retrieved neighbors
2. mean of per-segment ranked species scores after species alignment
3. max-pooling species score across member segments

If one aggregator clearly dominates and runtime becomes excessive, keep the best and expand formulas instead of expanding aggregator families further.

## Output contract

All run artifacts go under `results/threshold_full_classes/`.

Minimum outputs:

- `features_query_cache.json` — extracted query features + metadata
- `grouped_query_sets.json` — final grouped evaluation units
- `retrieval_results.csv` — one row per grouped query set
- `all_experiments.csv` — formula × algorithm × aggregator experiment table
- `best_strategy.json` — best grouped-F1 strategy summary
- `metrics_summary.json` — top-level counts and best metrics
- `analytics/` — confusion summaries, top-formula comparisons, distribution plots, and any helper tables
- `run.log` — execution log

## Analytics requirements

The analytics folder should include enough evidence to inspect whether a strategy is genuinely useful, not just numerically best.

At minimum produce:

- grouped confusion matrix counts
- grouped known-vs-unknown score distribution summary
- top-N strategy comparison table
- per-outcome example index (TP/FN/FP/TN grouped queries)
- comparison of top custom candidates by grouped F1

## Error handling

- skip unreadable images, but record them in the run log
- skip featureless/failed query segments, but keep set-level accounting visible
- if a grouped set loses all valid member segments, drop it and record the reason
- do not silently fall back to a different extractor or collection

## Testing and verification

Implementation verification should include:

- a focused automated test for grouped confusion/F1 accounting
- a focused automated test for grouped-query construction if the logic is factored cleanly
- repo validation relevant to touched code

Expected local checks after implementation:

- `uv --directory research run pytest tests/ -q`
- `uv --directory research run python -m ruff check src/experiments/threshold`

## Deliberate simplifications

- no weighted custom objective; standard grouped F1 only
- no new Qdrant upload step for incoming data
- no thesis/slides rewrite in this execution phase

## Success criteria

The task is complete when:

1. grouped-query threshold evaluation runs end-to-end against the original-only Qdrant collection
2. all metrics and analytics are written under `results/threshold_full_classes/`
3. best strategy is selected by grouped normal F1
4. outputs are reproducible from cached features and saved query-set definitions
5. verification checks pass or failures are explicitly captured
