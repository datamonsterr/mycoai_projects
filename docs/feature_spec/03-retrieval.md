# Feature Spec: Retrieval

## Overview

Given one or more segmented colony images from a single strain, retrieve the
most likely species by querying the Qdrant vector database of known fungal
features. The pipeline extracts visual features, performs KNN search, and
aggregates results across segments and media.

## User Stories

### 1. Species Classification

**As a** researcher
**I want** to submit segmented colony images and get species predictions
**So that** I can identify unknown fungal isolates

**Behavior:**
- Input: segmented colony images from one strain (1-3 segments per image,
  multiple images across different media)
- Pipeline:
  1. Feature extraction (EfficientNetB1 finetuned, ResNet50, etc.)
  2. Qdrant KNN search (k=5 default, configurable)
  3. Sibling filtering (exclude segments from same source image)
  4. Aggregation across segments (weighted by cosine similarity, or uniform)
  5. Environment strategy (same medium, all media, exclude medium)
- Output: ranked list of species with confidence scores

### 2. Configurable KNN

**As a** researcher
**I want** to adjust the KNN parameter k
**So that** I can balance precision vs recall

**Behavior:**
- Default k=5
- Configurable range: 1-20
- Higher k = more neighbors considered per segment
- Aggregation strategy also configurable:
  - **weighted**: cosine-similarity-weighted vote per neighbor
  - **uni**: uniform count (1/k per neighbor)

### 3. Environment Strategy

**As a** researcher
**I want** to control which growth media are included in the search
**So that** I can account for media-specific morphology

**Strategies (from fungal-cv-qdrant E1-E4):**

| Strategy | Behavior |
|----------|----------|
| Same medium (E1) | Only compare against colonies grown on the same medium |
| All media (E2) | Compare against all available media (no filter) |
| Specific medium (E3) | Query from one specific medium |
| Exclude medium (E4) | Exclude one medium from candidate pool |

**Behavior:**
- Default: Same medium (E1) — best accuracy for most cases
- Per-image setting: user may override per image in the batch

### 4. Multi-Media Query

**As a** researcher
**I want** to query using images of one strain grown on multiple media
**So that** I get more robust species classification

**Behavior:**
- One strain can have images on multiple media (e.g. MEA, CYA, YES)
- Each image is segmented independently
- All segments from all images of the same strain are aggregated together
- Final result: one ranked species list for the strain

## Acceptance Criteria

- [ ] Feature extraction pipeline runs on segmented colony crops
- [ ] Qdrant KNN search with configurable k (1-20)
- [ ] Configurable aggregation strategy (weighted / uni)
- [ ] Configurable environment strategy (E1/E2/E3/E4)
- [ ] Multi-media support: aggregate across images of same strain
- [ ] Ranked species results with confidence scores
- [ ] Results include top-5 species with per-species scores
- [ ] Response time under 5 seconds for single-image query

## Data Contract

**Query input** (from segmentation):

    {
      "strain": "string",
      "images": [
        {
          "image_id": "uuid",
          "media": "MEA",
          "segments": [{"segment_index": 0, "crop_path": "..."}]
        }
      ],
      "k": 5,
      "aggregation": "weighted",
      "environment_strategy": "E1"
    }

**Query output:**

    {
      "strain": "string",
      "rankings": [
        {"rank": 1, "species": "Penicillium commune", "score": 0.87},
        {"rank": 2, "species": "Penicillium expansum", "score": 0.43},
        ...
      ],
      "query_details": {
        "k": 5,
        "aggregation": "weighted",
        "environment_strategy": "E1",
        "total_neighbors_queried": 15
      }
    }

## Dependencies

- 02-segmentation.md (provides segmented colony crops)
- 04-visualization.md (consumes ranked results for display)
- Consumes: fungal-cv-qdrant Qdrant collection, feature extractors,
  aggregation logic (cross_validation.py, qdrant_query.py)
