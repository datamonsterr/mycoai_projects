# Fungal Species Retrieval Pipeline

```mermaid
flowchart TD
    A[Raw Petri Dish Images] --> B{Dataset Source}
    B -->|Original| C[curated_primary<br/>31 strains, 435 images]
    B -->|New Data| D[incoming_low_quality<br/>54 species, 460 images]
    
    C --> E[Image Preprocessing<br/>resize 256x256, median blur]
    D --> E
    
    E --> F[Prepared Dataset<br/>species/strain/media/angle/]
    
    F --> G{Segmentation Method}
    
    G -->|K-Means| H[HSV Color Space<br/>KMeans n=3<br/>Foreground Mask<br/>Spatial KMeans n=3<br/>Contour Refinement]
    G -->|YOLO| I[YOLOv11-seg<br/>conf ≥ 0.15<br/>IoU Filter 0.25<br/>Top-3 Boxes]
    
    H --> J[3 Colony Crops]
    I --> J
    
    J --> K[Feature Extraction]
    
    K --> L[Base Extractors:<br/>ResNet50, MobileNetV2<br/>EfficientNetB1, HOG, Gabor<br/>ColorHistogram]
    K --> M[Finetuned Extractors:<br/>EfficientNetB1_finetuned<br/>ResNet50_finetuned<br/>MobileNetV2_finetuned]
    
    L --> N[Qdrant Vector Index<br/>myco_fungi_features_full]
    M --> N
    
    N --> O{Query Phase}
    
    O --> P[Strain Query<br/>KNN Search]
    P --> Q[K-Nearest Neighbors<br/>K ∈ {3,5,7,9,11}]
    
    Q --> R{Aggregation Strategy}
    
    R -->|weighted| S[Score-Weighted<br/>Σscores / Σcounts]
    R -->|freq_strength| T[Freq × Strength<br/>query_freq × avg_score]
    R -->|relative| U[Relative Score<br/>Σscores / total_scores]
    
    S --> V[Species Prediction]
    T --> V
    U --> V
    
    V --> W{Environment Strategy}
    W -->|E1: Same Media| X[Match query environment<br/>with DB environment]
    W -->|E2: All Media| Y[Cross-environment retrieval]
    
    X --> Z[Threshold Classification<br/>Known vs Unknown]
    Y --> Z
    
    Z --> AA[Final Species ID]
    
    subgraph Validation
        BB[5-Fold Cross-Validation<br/>Strain-Level]
        CC[Per-Species Metrics<br/>F1, Precision, Recall]
        DD[Visualization<br/>Correct/Incorrect Cases]
    end
    
    AA --> BB
    BB --> CC
    CC --> DD
```

## Pipeline Components

### 1. Dataset Preparation
- **Structure**: `{root}/{species}/{strain}/{media}/{angle}/`
- **Roots**: `full_prepared/`, `original_prepared/`, `new_data_prepared/`
- **Artifacts per leaf**: source, prepared, bbox_kmeans, bbox_yolo, pipeline_kmeans, pipeline_yolo, segments_kmeans/, segments_yolo/

### 2. Segmentation
- **K-Means**: HSV color-space clustering (n=3), foreground mask, spatial K-Means (n=3) on foreground points, contour refinement
- **YOLO**: YOLOv11-seg with confidence threshold 0.15, IoU-based non-maximum suppression to keep top-3 non-overlapping boxes

### 3. Feature Extraction
- **Base**: ResNet50, MobileNetV2, EfficientNetB1, HOG, Gabor, ColorHistogram (HS concat)
- **Finetuned**: Same backbones fine-tuned on fungal colony classification

### 4. Retrieval
- **Qdrant**: Cosine distance, multiple named vectors per point
- **KNN**: Configurable K values (3-11)
- **Environment control**: Same-media (E1) or cross-media (E2) search
- **Aggregation strategies**: weighted, freq_strength, relative, uniform
- **Sibling filtering**: Exclude segments from same parent image

### 5. Cross-Validation
- 5-fold strain-level CV with round-robin assignment
- Fold manifests generated from the prepared segments metadata, mapping strain identities to fold indices
- Per-fold evaluation with full visualization of correct/incorrect predictions and aggregated accuracy metrics
