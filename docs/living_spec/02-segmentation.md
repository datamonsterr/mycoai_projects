<!-- spec: synced 2026-05-11T04:02:09Z from feature_spec/02-segmentation.md -->

# Feature Spec: Segmentation

## Overview

Auto-segment fungal colonies from uploaded plate images. Users can edit
bounding boxes and remove misdetected regions. Segmentation produces 1-3
colony crops per image.

## User Stories

### 1. Auto-Segmentation

**As a** researcher
**I want** the system to automatically detect and crop fungal colonies
**So that** I don't have to manually draw bounding boxes

**Behavior:**
- On upload, the system runs segmentation automatically
- Two methods available (configurable by data owner):
  - **KMeans**: HSV clustering + spatial clustering (best for uniform plates)
  - **Contour**: Canny edge detection + circularity filter (best for
    irregular colonies)
- Default: KMeans with K=3 clusters
- Result: 1-3 colony segments with bounding boxes overlaid on source image
- Each segment is cropped to a square region

### 2. Editable Bounding Boxes

**As a** researcher
**I want** to resize and reposition bounding boxes
**So that** I can correct the segmenter when it misdetects

**Behavior:**
- Bounding boxes rendered as draggable/resizable overlays on the source image
- Drag to move, corner handles to resize
- Maintain aspect ratio by default; hold Shift to free-resize
- Add new bbox: click/drag on empty area
- Delete bbox: select and press Delete or click remove button
- Changes are saved before proceeding to retrieval

### 3. Segment Removal

**As a** researcher
**I want** to remove individual segments
**So that** I exclude debris, reflections, or non-colony regions

**Behavior:**
- Each segment/bbox has a remove (X) button in the overlay
- Removed segments are not sent to the retrieval pipeline
- Removal is undoable until "Process" is clicked
- Minimum 1 segment must remain (enforced at UI level)

### 4. Batch Segmentation

**As a** researcher
**I want** to review and edit segmentations across an entire batch
**So that** I can quickly validate or correct many images

**Behavior:**
- Batch review shows all images with their bounding boxes in a grid
- Quick-approve: checkmark to accept current segmentations
- Quick-reject: flag an image for manual review later
- Navigation: next/previous image, jump to flagged

## Acceptance Criteria

- [ ] Auto-segmentation runs on upload with KMeans (default)
- [ ] Segmentation method configurable per batch (KMeans vs Contour)
- [ ] Bounding boxes are draggable and resizable
- [ ] New bbox creation via click-drag
- [ ] Bbox deletion via Delete key or remove button
- [ ] Segment removal with undo support
- [ ] Batch review grid with approve/reject per image
- [ ] Segmentation visualization (bbox overlay on source image)

## Data Contract

**Output per image** (consumed by retrieval pipeline):

    {
      "image_id": "uuid",
      "strain": "string",
      "media": "string",
      "segments": [
        {
          "segment_index": 0,
          "bbox": {"x": int, "y": int, "w": int, "h": int},
          "crop_path": "Dataset/prepared/.../segments/segment_1.jpg"
        }
      ],
      "segmentation_method": "kmeans"
    }

## Dependencies

- 01-image-input.md (receives uploaded images)
- 03-retrieval.md (consumes segment crops)
- Consumes: fungal-cv-qdrant segmentation pipeline outputs (kmeans.py,
  contour bboxes)
