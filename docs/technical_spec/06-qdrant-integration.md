# Technical Spec: Qdrant Integration

## Overview

Design the integration between the backend and the Qdrant vector database.
The backend must reimplement Qdrant connectivity following the contracts
established by fungal-cv-qdrant experiments, without importing directly.

---

## Collection Schema

**[DECISION: Collection strategy]**

Choices:
- A) **Single collection with named vectors** — matches fungal-cv-qdrant
  schema: one collection `myco_fungi_features_full_finetuned`, each point
  has multiple named vectors (ResNet50, EfficientNetB1, ViT, etc.)
  **(Recommended)**
- B) One collection per feature extractor — simpler queries per type
- C) Single collection, single vector (concatenated) — no named vectors

**Collection name:** `myco_fungi_features_full_finetuned` (from fungal-cv-qdrant config)

**Named vectors (from fungal-cv-qdrant experiment outputs):**

| Vector Name | Dimension | Extractor |
|---|---|---|
| `resnet50` | 2048 | ResNet50 (ImageNet) |
| `mobilenetv2` | 1280 | MobileNetV2 (ImageNet) |
| `efficientnetb1` | 1280 | EfficientNetB1 (ImageNet) |
| `hog` | dynamic | HOG descriptors |
| `gabor` | 32 | Gabor filter banks |
| `colorhistogram` | 96 | RGB histogram |
| `colorhistogramhs` | 64 | HSV histogram (H+S) |
| `ResNet50_finetuned` | 2048 | Fine-tuned ResNet50 |
| `MobileNetV2_finetuned` | 1280 | Fine-tuned MobileNetV2 |
| `EfficientNetB1_finetuned` | 1280 | Fine-tuned EfficientNetB1 |
| `ViT_finetuned` | 768 | Vision Transformer |
| `colorhistogramhsconcatresnet50` | 2112 | Combined HS histogram + ResNet50 |
| `efficientnetb1_triplet` | 1280 | Triplet-loss fine-tuned EfficientNetB1 |

**Distance metric:** Cosine

**Default query vector:** `EfficientNetB1_finetuned` (best accuracy from experiments)

---

## Qdrant Client Setup

**[DECISION: Qdrant client library]**

Choices:
- A) **qdrant-client (Python)** — official Python client, REST + gRPC,
  async support **(Recommended)**
- B) Direct REST API (httpx) — no library dependency
- C) qdrant-client with gRPC only — faster, fewer HTTP issues

**Configuration (from backend config.py):**

    class QdrantSettings(BaseSettings):
        model_config = SettingsConfigDict(env_prefix="MYCOAI_QDRANT_")
        host: str = "localhost"
        port: int = 6333
        grpc_port: int = 6334
        collection_name: str = "myco_fungi_features_full_finetuned"
        prefer_grpc: bool = False

---

## Core Operations

### 1. Query by Image

Reimplements `src/utils/qdrant_query.py::find_nearest_neighbors_by_image()`:

    Input: segment image path, feature_type (e.g. "EfficientNetB1_finetuned")
    Flow:
      1. Extract features from segment image using specified extractor
      2. Build Qdrant filter (environment, exclude_strain, etc.)
      3. Query Qdrant with feature vector + filter + k
      4. Return top-k neighbors with payload (species, strain, similarity)
    Output: List[Neighbor]

### 2. Query by Existing Point

Reimplements `find_nearest_neighbors_by_id()`:

    Input: qdrant_point_id, feature_type, k
    Flow:
      1. Retrieve the named vector from the point
      2. Query with that vector + filter
      3. Exclude self + siblings (same parent_item_id)
      4. Return top-k neighbors
    Output: List[Neighbor]

### 3. Upsert Points

For indexing new segmented images into Qdrant:

    Input: segment_id, feature_vectors (dict of name->vector), payload
    Flow:
      1. Extract all feature vectors for the segment
      2. Build Qdrant PointStruct with all named vectors + payload
      3. Upsert into collection
      4. Record qdrant_point_id in DB
    Output: qdrant_point_id

### 4. Delete Points

For archiving images/strains:

    Input: qdrant_point_ids (list)
    Flow:
      1. Delete points from Qdrant by ID
      2. Mark as inactive in qdrant_index_state
    Output: deleted count

### 5. Build Filters

Reimplements `build_filter()` for environment, strain, species, exclusion:

    Input: environment, exclude_strain, species_filter, exclude_ids
    Output: Qdrant Filter object

    Filter types:
      - Environment match: must=[{key:"environment", match:{value:"MEA"}}]
      - Same medium (E1): filter by environment = query_media
      - All media (E2): no filter
      - Specific medium (E3): filter by environment = specified_medium
      - Exclude medium (E4): must_not=[{key:"environment", match:{value:"MEA"}}]
      - Exclude strain: must_not=[{key:"strain", match:{value:"DTO 148-D1"}}]
      - Exclude siblings: must_not=[{key:"parent_item_id", match:{value:...}}]

---

## Aggregation Strategies

Reimplements logic from `src/lib/cross_validation.py`:

| Strategy | Formula |
|----------|---------|
| **weighted** | Score(species) = sum(cosine_similarity) for all neighbors of that species |
| **uni** | Score(species) = count(neighbors of that species) / k |
| **manual_weighted** | Score(species) = sum(weight[species][extractor] * similarity) |

---

## Collection Management

**[DECISION: Collection creation strategy]**

Choices:
- A) **Assume collection exists (created by fungal-cv-qdrant pipeline)** —
  backend only reads/updates, collection is prepared offline
  **(Recommended for development)**
- B) Auto-create on startup if not exists — self-contained
- C) Migration scripts — explicit creation with versioning

**[DECISION: How to handle the "learned" gap]**

When users upload new images (not from curated dataset), they need to be
indexed before retrieval can find them.

Choices:
- A) **Index on upload** — immediately extract features and upsert to
  Qdrant. "learned" = "indexed in Qdrant" **(Recommended)**
- B) Batch index periodically — manual trigger by data owner
- C) No new indexing — only pre-indexed curated data is searchable

---

## Feature Extraction Integration

**[DECISION: How to run feature extraction]**

Choices:
- A) **Call fungal-cv-qdrant scripts via subprocess** — reuse existing
  extractors without duplicating code **(Recommended for speed)**
- B) Reimplement extractors in backend — cleaner architecture, code
  duplication but follows reimplementation rule
- C) Load models as Python imports — violates reimplementation rule,
  tight coupling

Note: The reimplementation rule says "inspect experiment code, reimplement
in backend, do NOT import directly." However, for the feature extraction
models themselves (PyTorch weights), the most practical approach is:

- **Option D) Extractors as a shared library** — extract feature extraction
  into a standalone `mycoai_ml` package that both fungal-cv-qdrant and
  backend import. This is the cleanest long-term approach.

**[DECISION: Feature extraction deployment]**

Choices:
- A) **Subprocess calls to fungal-cv-qdrant scripts** — fastest path,
  experiments already run this way. Backend wraps in Celery task.
  **(Recommended for MVP)**
- B) Extractors as shared library — clean but requires refactoring
  fungal-cv-qdrant
- C) Microservice — separate GPU service for extraction
- D) Reimplement from scratch — most compliant with rules, slowest

---

## Performance Considerations

- Connection pooling: Qdrant client is thread-safe, reuse one instance
- Batch upsert: index all segments for one image in one API call
- Caching: cache collection info (vector names, dimensions) on startup
- Timeout: set 30s timeout for queries, 300s for batch indexing
