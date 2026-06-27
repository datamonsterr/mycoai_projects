# Fungal Species Retrieval Pipeline

```mermaid
flowchart TD
    A[Raw Petri Dish<br/>Images] --> S1

    subgraph S1["Stage 1: Preprocessing & Colony Segmentation"]
        direction LR
        P1[Resize 256×256<br/>Circle Detection<br/>Background Masking<br/>Crop to Dish] --> P2{Segmentation}
        P2 -->|K-Means| P3[HSV K=2 Clustering<br/>Local K=2 Shrink<br/>Bounding Box]
        P2 -->|YOLO| P4[YOLO26n-seg<br/>Top-3 Detections<br/>Instance Masks]
        P3 --> P5[Colony Segments<br/>~3 per plate]
        P4 --> P5
    end

    S1 --> S2

    subgraph S2["Stage 2: Feature Extraction & Vector Indexing"]
        direction LR
        Q1{Extractor Family} -->|Hand-crafted| Q2[HOG · Gabor<br/>ColorHist · ColorHistHS]
        Q1 -->|Pretrained DL| Q3[ResNet50 · EfficientNetB1<br/>MobileNetV2<br/>ImageNet weights]
        Q1 -->|Fine-tuned DL| Q4[ResNet50 · EfficientNetB1<br/>MobileNetV2<br/>Fungal-trained weights]
        Q2 --> Q5[L2-Normalize<br/>Embedding Vectors]
        Q3 --> Q5
        Q4 --> Q5
        Q5 --> Q6[(Qdrant<br/>Vector DB<br/>Cosine Index)]
    end

    S2 --> S3

    subgraph S3["Stage 3: KNN Retrieval & Multi-Image Aggregation"]
        direction LR
        R1[Query Colony<br/>Extract Feature] --> R2[Cosine Search<br/>Top-K Neighbors<br/>K=7]
        R2 --> R3[Filter Siblings<br/>Exclude Same Parent]
        R3 --> R4{Aggregation}
        R4 -->|weighted| R5[Score-Weighted<br/>Σscores / total_neighbors]
        R4 -->|freq_strength| R6[Freq × Strength<br/>query_freq × avg_score]
        R4 -->|relative| R7[Relative<br/>Σscores / Σ all scores]
        R5 --> R8[Strain-Level<br/>Species Ranking]
        R6 --> R8
        R7 --> R8
    end

    S3 --> S4

    subgraph S4["Stage 4: Species Prediction & Validation"]
        direction LR
        T1[Top-1 Species<br/>with Confidence Score] --> T2[Threshold Check<br/>Known vs Unknown]
        T2 --> T3[Final Species ID<br/>or Reject as Unknown]
        T3 --> T4[5-Fold Cross-Validation<br/>Per-Species F1 · Precision · Recall]
    end

    S4 --> OUT[Output:<br/>Species Prediction<br/>with Retrieval Evidence]
```

## Pipeline Stages — Detailed Breakdown

### Stage 1: Preprocessing & Colony Segmentation

**Input:** Raw Petri dish microscopy images (435 curated + 460 incoming, 8 Penicillium species)

1. **Dish Detection & Crop:** Hough Circle Transform detects dish boundary → background masked → cropped to dish region.
2. **Resize:** Standardized to 256×256 pixels.
3. **Colony Segmentation (two methods):**
   - **K-Means (primary):** HSV color-space K=2 clustering separates colony foreground from agar background. Local K=2 Shrink mitigates agar flare on MEA/YES media by re-clustering per-colony regions and eroding halo pixels.
   - **YOLO26n-seg (alternative):** Fine-tuned instance segmentation model trained on 303 labeled colony images, producing polygon masks with confidence ≥ 0.15.
4. **Output:** ~3 colony segment crops per dish (typically 9 segments per strain: 3 colonies × 3 media conditions).

### Stage 2: Feature Extraction & Vector Indexing

**Input:** Segmented colony images (256×256×3 RGB)

1. **Feature Extractors (3 families):**
   - **Hand-crafted (TR):** HOG (3,780-dim gradient orientation), Gabor (40-dim texture), ColorHistogram (96-dim RGB), ColorHistogramHS (64-dim Hue+Saturation).
   - **Pretrained Deep Learning (PT):** ResNet50, EfficientNetB1, MobileNetV2 with ImageNet-1K weights — backbone only, classifier removed, output pooled features (1,280–2,048-dim).
   - **Fine-tuned Deep Learning (FT):** Same architectures fine-tuned on 1,011 fungal colony images (8 species, 24 strains) via cross-entropy classification proxy task.
2. **L2 Normalization:** All vectors normalized to unit length for cosine similarity comparison.
3. **Vector Database:** Points indexed in Qdrant with multi-vector support (each extractor produces a named vector). Payload includes strain ID, species label, growth medium, camera angle, segment index. Collection: `myco_fungi_features_full`.

### Stage 3: KNN Retrieval & Multi-Image Aggregation

**Input:** Query colony image → feature vector v_q

1. **Cosine Nearest Neighbor Search:** Top-K neighbors retrieved from Qdrant (K=7). Query strain's own vectors excluded.
2. **Sibling Filtering:** Neighbors from the same parent Petri dish image as the query segment are removed to prevent data leakage.
3. **Multi-Image Aggregation (3 strategies):**
   - **weighted:** `scores[X] / total_neighbors` — fraction of total similarity mass belonging to species X.
   - **freq_strength:** `(queries_with_X / M) × (scores[X] / count[X])` — how often X appears × average match strength.
   - **relative:** `scores[X] / Σ all_scores` — share of total evidence, naturally summing to 1.
4. **Output:** Sorted species ranking with confidence scores.

### Stage 4: Species Prediction & Validation

**Input:** Aggregated species scores per test strain

1. **Top-1 Prediction:** Highest-scoring species selected as prediction.
2. **Threshold Classification:** Formula applied to top-K scores determines known vs unknown — thresholds optimized via F1-grid search, ROC Youden's J, or Otsu's method.
3. **5-Fold Cross-Validation:** Strain-level stratified folds, 45 evaluation configurations (3 aggregations × 3 K values × 5 folds). Metrics: per-species accuracy, F1, precision, recall.
4. **Output:** Final species prediction with retrieval evidence visualization (query + top neighbors).
