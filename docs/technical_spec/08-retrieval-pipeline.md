# Technical Spec: Retrieval Pipeline

## Overview

Design the backend retrieval pipeline that orchestrates feature extraction,
Qdrant KNN search, and result aggregation to produce ranked species
predictions.

**Use case references**: UC-RETRIEVE-01 (includes UC-PREP-01).<br>
**Feature spec references**: FR-030 (configurable KNN, k=1–20), FR-031 (multi-Media queries).

---

## Pipeline Flow

### Single Image Query

    1. Receive: image_id (already segmented)
    2. Load: segments from DB for this image
    3. For each segment (1-3):
       a. Extract features (EfficientNetB1_finetuned)
       b. Query Qdrant with k neighbors
       c. Filter siblings (same parent_item_id)
       d. Return top-k neighbors per segment
    4. Aggregate across segments:
       a. Collect all neighbors from all segments
       b. Apply aggregation strategy (weighted / uni)
       c. Rank species by aggregated score
    5. Return: ranked species list

### Multi-Image / Multi-Media Query (Strain-level)

    1. Receive: list of image_ids for one strain (across media)
    2. For each image:
       a. Run single-image query pipeline (steps 3-4 above)
    3. Aggregate across images (same as step 4 above):
       a. All neighbors from all images of the strain
       b. Apply aggregation strategy
       c. Rank species
    4. Return: one ranked species list for the strain

### Batch Query

    1. Receive: list of strains, each with list of images
    2. For each strain, run multi-image query pipeline
    3. All results in parallel (Celery chords/groups)
    4. Progress tracking per strain
    5. Return: results per strain

---

## Environment Strategy Implementation

The retrieval pipeline supports two environment strategies (per FR-031):

**Same-media**: Filter Qdrant search to vectors whose `environment` field
matches the query media type. Used for Known Media queries.

**All-media**: No environment filter applied. Use for New/other Media queries.

```python
def build_environment_filter(strategy, query_media):
    """
    same_media:   Filter by query_media
    all_media:    No filter
    """
    if strategy == "same_media":
        return Filter(must=[FieldCondition(
            key="environment",
            match=MatchValue(value=query_media)
        )])
    elif strategy == "all_media":
        return None
```

Configurable KNN (`k` = 1–20, per FR-030) is passed to the Qdrant search
call and applies to both aggregation methods (weighted and uniform).

---

## Aggregation Implementation

### Weighted (cosine-similarity-weighted vote)

    for each neighbor in all_neighbors:
        species_scores[neighbor.species] += neighbor.similarity

    ranked = sorted(species_scores, key=species_scores.get, reverse=True)

### Uniform (1/k per neighbor)

    for each neighbor in all_neighbors:
        species_scores[neighbor.species] += 1.0 / k

    ranked = sorted(species_scores, key=species_scores.get, reverse=True)

### Manual Weighted (per-species weights from species_weights.json)

    for each neighbor in all_neighbors:
        weight = species_weights.get(neighbor.species, {}).get(extractor, 1.0)
        species_scores[neighbor.species] += neighbor.similarity * weight

    ranked = sorted(species_scores, key=species_scores.get, reverse=True)

---

## Feature Extractor Selection

**[DECISION: Which feature extractor to use as default]**

Choices:
- A) **EfficientNetB1_finetuned** — best accuracy in cross-validation
  experiments, 1280-dim, fast **(Recommended)**
- B) ViT_finetuned — 768-dim, newer architecture, potentially better
- C) Ensemble (multiple extractors) — best accuracy, slower, more complex
- D) User-selectable — expose choice in UI

**[DECISION: Feature extractor ensemble strategy (future)]**

Choices:
- A) Weighted average of per-extractor rankings — simple, good results
  in ensemble experiments **(Recommended for Phase 2)**
- B) Concatenated vectors — requires Qdrant collection change
- C) Voting across extractors — majority species wins

---

## Caching Strategy

**[DECISION: Which results to cache]**

Choices:
- A) **Cache Qdrant query results per segment** — most expensive step,
  cache by (segment_id, feature_type, k, env_strategy) for 1 hour.
  Invalidate on re-index. **(Recommended)**
- B) Cache full retrieval results per strain — simpler, less granular
- C) No caching — always live query, always fresh
- D) Cache extracted feature vectors — re-extraction is expensive

---

## Concurrency

**[DECISION: How to parallelize batch queries]**

Choices:
- A) **Celery group: one task per strain, aggregate when all complete** —
  scales horizontally, fault-tolerant **(Recommended)**
- B) asyncio.gather in single process — limited by GIL, simpler
- C) Sequential — simplest, slowest

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| Segment has no features | Skip segment, log warning |
| Qdrant returns 0 results | Return empty neighbors, continue |
| Feature extractor fails | Retry 3x, then mark segment as failed |
| All segments fail | Return error to user with details |
| Partial batch failure | Return results for succeeded strains, errors for failed |

---

## Evaluation Metrics

Track per-query and aggregate:

- Response time (p50, p95, p99)
- Number of neighbors retrieved
- Query success rate
- Qdrant query time vs feature extraction time

---

## Sync vs Async Query

**[DECISION: Small query path]**

For single-image queries (fast enough for synchronous):

Choices:
- A) **Async first: everything via Celery jobs** — consistent API,
  polling or WebSocket for results. Unified experience.
  **(Recommended)**
- B) Sync for single query, async for batch — two code paths
- C) Sync for everything under timeout, async otherwise
