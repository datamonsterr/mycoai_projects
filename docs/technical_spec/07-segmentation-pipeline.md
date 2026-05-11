# Technical Spec: Segmentation Pipeline

## Overview

Design how the backend invokes segmentation on uploaded images, caches
results, and surfaces editable bounding boxes to the frontend.

---

## Segmentation Methods

From fungal-cv-qdrant experiments:

### KMeans Method

    Source: src/preprocessing/kmeans.py
    Pipeline:
      1. Convert image to HSV
      2. K=3 KMeans clustering on HSV pixels
      3. Select foreground label (non-background cluster)
      4. Spatial K=2/3 clustering for individual colonies
      5. Bounding box refinement (erosion, contour fit, halo shrink)
      6. Output: [{x, y, w, h}] for 1-3 bboxes
    Strengths: Uniform plates with clear colony-background contrast
    Weaknesses: Struggles with irregular colonies, debris

### Contour Method

    Source: src/prepare/dataset.py::_contour_bboxes()
    Pipeline:
      1. Canny edge detection
      2. Morphological close (connect nearby edges)
      3. Find contours
      4. Circularity filter: score = area * circularity
      5. Select top-3 by score
      6. Output: [{x, y, w, h}] for 1-3 bboxes
    Strengths: Better on irregular colonies, less sensitive to lighting
    Weaknesses: Can pick up plate edges, text, debris

---

## Integration Strategy

**[DECISION: How backend invokes segmentation]**

Choices:
- A) **Wrap fungal-cv-qdrant scripts as Celery tasks** — invoke
  segment_item() via subprocess, capture JSON output to STDOUT, parse
  in backend. Matches existing experiment workflow. **(Recommended)**
- B) Reimplement segmentation in backend — clean separation, code
  duplication, slower to develop
- C) Shared library — extract segmentation into mycoai_segmentation pkg
- D) GPU microservice — separate service, async, overkill for CPU-based
  KMeans/Contour

**Execution flow:**

    1. User uploads image
    2. Backend saves image to Dataset/uploads/{user_id}/{strain}/{media}/
    3. Celery task: runs segmentation script
       - Input: image path, method ("kmeans")
       - Output: JSON with bboxes, segment crop paths, pipeline image path
    4. Backend reads JSON output, creates DB records for segments
    5. Backend returns segment info to frontend (bboxes + crop URLs)
    6. Frontend renders bbox overlay on image

---

## Bounding Box Data Flow

### Backend -> Frontend

The backend serves segment data:

    GET /api/v1/images/{id}
    Response:
    {
      "image_id": "uuid",
      "source_url": "/api/v1/images/{id}/source",
      "segments": [
        {
          "segment_id": "uuid",
          "segment_index": 0,
          "bbox": {"x": 45, "y": 60, "w": 80, "h": 80},
          "crop_url": "/api/v1/images/{id}/segments/0/crop",
          "pipeline_url": "/api/v1/images/{id}/pipeline"
        }
      ],
      "segmentation_method": "kmeans"
    }

### Frontend -> Backend (edits)

When user edits bounding boxes:

    PATCH /api/v1/images/{id}/segments
    Body:
    {
      "segments": [
        {
          "segment_index": 0,
          "bbox": {"x": 50, "y": 55, "w": 85, "h": 90}
        },
        {
          "segment_index": 1,
          "bbox": {"x": 200, "y": 100, "w": 75, "h": 75}
        }
      ],
      "deleted_segments": [2]  // segment_index 2 removed
    }

The backend re-crops segments with updated bboxes and re-runs feature
extraction before retrieval.

---

## Image Processing Pipeline

For each image, the system produces (from fungal-cv-qdrant):

    uploads/{strain}/{media}/{image_id}/
    +-- source.jpg                  # Original uploaded image
    +-- prepared.jpg                # 256x256 preprocessed (center-cropped,
    |                                # plate mask applied)
    +-- bbox_{method}.jpg           # Bbox overlay visualization
    +-- pipeline_{method}.jpg       # 3-panel visualization (source|prep|bbox)
    +-- segments/
        +-- segment_0.jpg           # Cropped colony segment
        +-- segment_1.jpg
        +-- segment_2.jpg

---

## Image Serving

**[DECISION: How to serve images to frontend]**

Choices:
- A) **FastAPI StaticFiles + file path URLs** — mount `Dataset/` as
  static, serve via `/static/uploads/...`. Simple, no pre-signed URLs.
  **(Recommended for dev)**
- B) Dedicated image endpoint with streaming — `/api/v1/images/{id}/file`,
  more control (auth, resizing)
- C) S3 pre-signed URLs — cloud-ready, time-limited access

---

## Preprocessing (Plate Detection)

Before segmentation, images may need preprocessing:

1. **Petri dish detection**: Find circular plate, crop to square
2. **Plate mask**: Mask out background outside dish
3. **Resize**: 256x256 standard size

**[DECISION: Where preprocessing happens]**

Choices:
- A) **Same Celery task as segmentation** — single pipeline: preprocess
  -> segment -> output **(Recommended)**
- B) Separate preprocessing step with UI confirmation — user approves
  crop before segmentation
- C) No preprocessing — segment raw image directly (less accurate)

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| Single image segmentation | < 3 seconds |
| Batch (100 images) | < 5 minutes |
| Bbox edit + re-crop | < 1 second |
| Feature extraction per segment | < 500ms |
