<!-- spec: synced 2026-05-19T00:00:00Z from feature_spec/01-image-input.md -->

# Feature Spec: Image Input

## Overview

Users upload fungal colony images and run species classification. The system
supports single-image classification and batch processing with a template
folder structure.

## User Stories

### 1. Single Image Upload

**As a** researcher
**I want** to upload one image of a fungal strain grown on one medium
**So that** I can classify its species

**Rules:**
- One image = one strain x one medium x N colonies (N configurable)
- Image formats: JPEG, PNG, TIFF (minimum 256x256)
- Upload shows a preview before processing
- User must specify the growth medium from a predefined list
- User must specify the strain identifier (free text)

**Predefined Media Set:** MEA, CYA, YES, DG18, OA, CREA, PDA, CMA, SAB, M40Y
(subject to expansion)

### 2. Max Colonies Configuration

**As a** researcher
**I want** to set the maximum number of colonies per image
**So that** I control segmentation sensitivity

**Behavior:**
- Default: model built-in confidence threshold (no override)
- User can set an integer max (e.g. 3 colonies per plate)
- Setting overrides confidence threshold: system picks top-N by score
- Valid range: 1-10

### 3. Batch Processing

**As a** researcher
**I want** to upload a folder of images with metadata
**So that** I can classify hundreds of samples at once

**Template folder structure:**

    batch_upload/
    +-- template.json          # Column mappings + config
    +-- strain_001/
    |   +-- metadata.csv       # strain, media, notes per image
    |   +-- image_01.jpg
    |   +-- image_02.jpg
    +-- strain_002/
        +-- ...

**template.json schema:**

    {
      "batch_name": "string",
      "column_mapping": {
        "strain": "column_name_in_csv",
        "media": "column_name_in_csv",
        "max_colonies": "column_name_in_csv (optional)"
      },
      "defaults": {
        "media": "MEA",
        "max_colonies": null
      },
      "output_format": "csv"
    }

**AI reformat commands:** The system provides a CLI/API to reformat arbitrary
folder structures into the template format. AI-assisted column detection and
mapping.

### 4. Image Removal (Batch Context)

**As a** researcher
**I want** to remove individual images from a batch before processing
**So that** I can exclude poor-quality samples

**Behavior:**
- In batch review, each image has a remove button
- Removed images are skipped, not deleted
- Removal is undoable until processing starts

## Acceptance Criteria

- [ ] Single image upload with strain + media selection
- [ ] Max colonies slider (1-10) with "default (model threshold)" option
- [ ] Batch folder upload with template.json parsing
- [ ] Batch preview showing image count per strain, removable per image
- [ ] AI-assisted column mapping from arbitrary CSVs
- [ ] Progress indicator during batch processing
- [ ] Downloadable results CSV after batch completion

## Dependencies

- 02-segmentation.md (segments each uploaded image)
- 03-retrieval.md (classifies each segment)
- 08-roles-and-permissions.md (data owner can link directly to species)
