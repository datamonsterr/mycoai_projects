# Terminology Reference

This document defines the key terms, strategies, and concepts used throughout the project.

---

## Domain Knowledge

### Colony
A single fungal colony growing on a petri dish plate. A plate may contain **1–3 colonies** depending on the experimental setup. Each colony is photographed from two sides (obverse / reverse) and under various imaging conditions.

### Strain
A specific fungal isolate (culture) used in experiments. Each strain belongs to exactly one species. Strains are identified by a unique identifier, e.g., `DTO 123-A1`. Strains are the **unit of test/train splitting** — in cross-validation, evaluation is **leave-one-strain-out**: one held-out strain is tested at a time while all remaining strains stay in the training/reference pool for that fold.

**Leakage rule:** a held-out test strain must never appear in the fine-tuning training set or in the retrieval candidate pool for the same benchmark fold.

### Species
The taxonomic classification target. The project classifies **5 *Penicillium* species**:
- *Penicillium citreonigrum*
- *Penicillium commune*
- *Penicillium crustosum*
- *Penicillium expansum*
- *Penicillium chrysogenum*

A species may have multiple strains.

### Media
The growth medium used to culture the colony. Each strain is grown on multiple Media values, which increase retrieval diversity. Common Media: `MEA`, `CYA`, `DG18`.

`environment` remains an internal code field and experiment label. User-facing docs should prefer `Media`.

### Plate / Petri Dish
The physical container on which a colony grows. One plate typically contains one colony, photographed from two angles.

---

## Environment Strategies (E1–E4)

These internal experiment strategies control **which Media values are included in the candidate pool** when retrieving neighbours for a query image.

### E1 — Same Environment (Default)
> **Query images are matched only against neighbours from the same growth medium.**

- The query environment is detected from the image metadata.
- Only candidates with `environment == query_environment` are considered.
- **Use when:** you want to simulate a controlled lab retrieval scenario, or when the query medium is known at inference time.
- Implementation: `environment=None` in Qdrant query → `find_nearest_neighbors_by_id` filters by the query's own environment.

### E2 — All Environments
> **Query images are matched against neighbours from ALL available growth media.**

- No environment filter is applied during retrieval.
- All environments contribute to the final aggregated score.
- **Use when:** you want maximum retrieval recall, or when the medium of the query is unknown / mixed.

### E3\_`<ENV>` — Query from Specific Environment
> **Only query images from one specific medium are used; retrieve from that same medium only.**

- Example: `E3_MEA` — query only uses images grown on MEA, candidate pool also restricted to MEA.
- **Use when:** evaluating how well the system performs when restricted to a single medium.

### E4\_`<ENV>` — Exclude One Environment
> **Query images come from all environments except the excluded one; the excluded medium is removed from the candidate pool.**

- Example: `E4_CYA` — query images may be from MEA, DG18, etc., but no CYA candidates are retrieved.
- **Use when:** testing cross-medium generalization (does the model still work if one medium is unavailable?).

---

## Aggregation Strategies

These strategies control **how neighbour similarity scores are combined** into a species-level prediction.

### Weighted (Score-Weighted)
> **Each neighbour votes for a species with a weight proportional to its cosine similarity score. The species with the highest total weighted score wins.**

Also called: `weighted`, `score`, `weighted_sum`.

Math:
```
species_score[s] = Σ  cosine_similarity(neighbour_i)   for all neighbours where neighbour_i.species == s
prediction = argmax_s species_score[s]
```

This is the **default and recommended** strategy — high-similarity matches have more influence.

### Uni (Uniform / Unweighted)
> **Each neighbour contributes an equal vote (1/k) to its species, regardless of similarity score.**

Also called: `uni`, `uniform`, `count`.

Math:
```
species_count[s] = Σ  1   for all neighbours where neighbour_i.species == s
prediction = argmax_s species_count[s]
```

Useful when similarity scores are unreliable or when you want to give rare species a fairer chance.

### Manual Weighted (Per-Species)
> **Species-specific weights from `species_weights.json` are applied on top of score-weighted aggregation.**

- Allows fine-grained tuning: reduce the influence of a model that over-predicts a specific species.
- `0.0` = completely disable that model for that species.
- `1.0` = standard weight.
- `< 1.0` = reduced influence.

---

## Retrieval Pipeline

```
Query Plate Image
  → Preprocess (crop petri dish)
  → Segment (KMeans / Contour / YOLO, or full-image baseline)
  → Feature Extraction (hand-crafted / pretrained / finetuned)
  → Qdrant KNN Retrieval (k neighbours)
  → Exclude held-out test strain from candidate pool
  → Aggregate per-segment or per-image neighbours
  → Species Ranking + Unknown Threshold + Evidence  ← FINAL OUTPUT
```

**Benchmark rule:** evaluation queries must be processed fresh from image files. Do not benchmark by looking up a held-out query image already stored inside Qdrant.

---

## Train / Test Split

Closed-set evaluation uses **leave-one-strain-out** testing. One held-out strain is evaluated at a time; all remaining strains are the allowed training/reference pool for that fold.

Open-set evaluation uses two separate tracks:
- **Unseen-strain track** — known species, unseen held-out strains
- **Unseen-species track** — species absent from the reference database

In cross-validation, held-out strains rotate round-robin across all strains of each species.

---

## Experiment Naming (autoresearch)

Experiments follow the branch naming convention:
```
autoresearch/{experiment-name}/{N}-{summary}
```
Where:
- `{experiment-name}` — e.g., `segmentation`, `feature-extractor`, `embedding-lr`
- `{N}` — sequential experiment attempt number (1, 2, 3, ...)
- `{summary}` — short description of the change in this attempt

Example: `autoresearch/segmentation/2-kmeans-params`

The **best result** is merged back to `autoresearch/{experiment-name}` (no attempt number suffix).
