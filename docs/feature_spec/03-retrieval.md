# Feature Spec: Retrieval

## Overview

Given one or more segmented colony images from one strain, retrieve likely Species by querying the Qdrant vector database of known fungal features. The pipeline extracts visual features, performs KNN search, and aggregates results across segments and media.

## User Stories

### 1. Retrieve Species

**As a** User
**I want** to upload strain images, segment colonies, and retrieve species predictions
**So that** I can identify unknown fungal isolates from one strain

**Behavior:**
- Input: one or more strain images with strain and Media metadata
- Retrieval includes upload, segmentation, bounding-box review, and results review
- Species metadata is not required for retrieval
- Pipeline:
  1. Upload single image or batch folder
  2. Download Batch Template Folder when needed
  3. Auto segment colonies with AI (see UC-PREP-01 Prepare Segmented Images)
  4. Allow bounding-box edits before processing
  5. Feature extraction
  6. Qdrant KNN search
  7. Aggregation across segments/images
  8. View ranked Species results with confidence scores
  9. Submit feedback or contribution proposal if desired

### 2. Known and New Media Strategy

**As a** User
**I want** retrieval to handle known and new growth media
**So that** I can still retrieve when my uploaded Media is not yet managed

**Behavior:**
- Known managed Media: default KNN compares against reference images from the same Media
- New/other Media: KNN compares against all available Media
- New/other Media is flagged for Data Owner review
- Data Owner can accept new Media into managed list or map it to an existing Media

### 3. Configurable KNN

**As a** User
**I want** to adjust the KNN parameter k
**So that** I can balance precision vs recall

**Behavior:**
- Default k=5
- Configurable range: 1-20
- Aggregation strategy configurable:
  - **weighted**: cosine-similarity-weighted vote per neighbor
  - **uni**: uniform count

### 4. Multi-Media Query

**As a** User
**I want** to query using images of one strain grown on multiple Media
**So that** I get more robust species classification

**Behavior:**
- One strain can have images on multiple Media
- Each image is segmented independently
- All segments from all images of the same strain are aggregated together
- Final result: one ranked Species list for the strain

### 5. Batch Retrieval

**As a** User
**I want** to upload a batch folder and view/download batch results
**So that** I can classify many samples at once

**Behavior:**
- User downloads Batch Template Folder with structure and restructuring instructions
- User uploads structured batch folder
- System previews uploaded images and metadata
- User can browse/search/filter uploaded batch data before processing
- User can remove unwanted uploaded images before segmentation/retrieval
- System auto-segments batch images and allows batch bbox review
- Results table includes image, strain, Media, predicted Species, confidence, bbox status, feedback/contribution status
- Results CSV is downloadable

## Acceptance Criteria

- [ ] Authentication required before retrieval workflow starts
- [ ] Upload captures strain and Media metadata
- [ ] Batch Template Folder includes restructuring instructions
- [ ] Batch preview allows browse/search/filter of uploaded images and metadata
- [ ] AI auto-segmentation runs before retrieval
- [ ] Bounding boxes are editable before retrieval
- [ ] Same-Media KNN for managed Media
- [ ] All-Media KNN for new/other Media
- [ ] New/other Media flagged for Data Owner review
- [ ] Qdrant KNN search with configurable k (1-20)
- [ ] Configurable aggregation strategy (weighted / uni)
- [ ] Multi-Media support: aggregate across images of same strain
- [ ] Ranked Species results with confidence scores
- [ ] Batch results CSV download
- [ ] Feedback/contribution entry point from results view
- [ ] Response time under 5 seconds for single-image query after segmentation

## Data Contract

**Query input** (from segmentation):

    {
      "strain": "string",
      "images": [
        {
          "image_id": "uuid",
          "media": "MEA | other free text",
          "segments": [{"segment_index": 0, "crop_path": "..."}]
        }
      ],
      "k": 5,
      "aggregation": "weighted"
    }

**Query output:**

    {
      "strain": "string",
      "media_strategy": "same_media | all_media",
      "rankings": [
        {"rank": 1, "species": "Penicillium commune", "score": 0.87},
        {"rank": 2, "species": "Penicillium expansum", "score": 0.43}
      ],
      "query_details": {
        "k": 5,
        "aggregation": "weighted",
        "total_neighbors_queried": 15,
        "new_media_flagged": false
      }
    }

## Dependencies

- 01-image-input.md (upload and batch template)
- 02-segmentation.md (segmented colony crops)
- 04-visualization.md (ranked results display)
- 05-feedback-pipeline.md (feedback/contribution from results)
- ../SRS.md UC-RETRIEVE-01
