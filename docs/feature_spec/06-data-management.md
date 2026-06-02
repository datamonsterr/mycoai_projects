# Feature Spec: Data Management

## Overview

Data Owners manage reference dataset records and managed metadata. Dataset records include image metadata, strain, media, species, segmentation/bounding boxes, archive state, and Qdrant index state. Users cannot browse or mutate the reference dataset.

## User Stories

### 1. Index New Data

**As a** Data Owner
**I want to** upload strain images for known Species and index them as reference data
**So that I** can expand retrieval coverage

**Behavior:**
- Index New Data reuses upload, auto-segmentation, editable bounding boxes, and review from the retrieval preparation workflow
- Index New Data does not include Retrieve Species because prediction is bypassed
- Required metadata: Species, strain, Media
- Segments are indexed into Qdrant with known Species metadata
- Supports batch indexing with Species metadata in folder structure/template
- Accepted contribution feedback enters pending reference data; Data Owner reviews metadata and bounding boxes before indexing

### 2. Manage Metadata

**As a** Data Owner
**I want to** CRUD Species and Media
**So that** retrieval and indexing use governed metadata values

**Behavior:**
- Species names must be unique case-insensitively
- Media names must be unique case-insensitively
- Data Owner can create Species/Media during indexing or feedback review
- Data Owner can accept new/other Media into managed Media or map it to existing Media
- Data Owner can map free-text suggested species to existing Species or create Species during review
- Strain is image metadata/dataset entity, not managed metadata catalog

### 3. Browse Dataset

**As a** Data Owner
**I want to** browse, search, filter, and group dataset records
**So that I** can understand and govern reference data

**Filters and grouping:**
- Search by strain
- Filter by Species
- Filter by Media
- Filter by date added
- Filter by data source
- Filter by Data Update Status
- Group by strain, Media, Species

**Overview Dashboard:**

| Metric | Description |
|--------|-------------|
| Total images | Count of active images |
| Total strains | Distinct strain count |
| Total species | Distinct Species count |
| Total media types | Distinct Media count |
| Images per species | Species distribution |
| Images per medium | Media distribution |
| Index status | Current vs updated_requires_reindex vs archived |

### 4. Update Dataset Records

**As a** Data Owner
**I want to** update image metadata and bounding boxes
**So that** reference data stays correct

**Behavior:**
- Editable metadata: Species, strain, Media
- Editable segmentation/bounding boxes
- Metadata or bbox changes mark item `updated_requires_reindex`
- System warns: "This update requires Qdrant re-indexing before retrieval reflects the change."
- Update is audited

### 5. Archive and Restore

**As a** Data Owner
**I want to** archive or restore incorrect or obsolete data
**So that I** keep the dataset clean while preserving auditability

**Behavior:**
- Archive is reversible
- Permanent delete is not supported
- Archived data is excluded from Qdrant queries
- Archived data is excluded from future indexing/retraining datasets
- Restore moves item back to active state and marks it for re-index when needed
- System warns when many archived/updated/accepted records indicate external retraining may be needed

### 6. Qdrant Re-index Awareness

**As a** Data Owner
**I want to** see which records require re-indexing
**So that** retrieval uses current reference data

**Behavior:**
- Data Update Status values: `current`, `updated_requires_reindex`, `archived`
- Changed metadata, changed boxes, accepted corrections, accepted contributions, and restores can require re-indexing
- Data Owner can trigger Qdrant re-indexing through Maintain Model and Index

## Data Model

**Species:**

    {
      "species_id": "uuid",
      "name": "string (unique)",
      "description": "string | null",
      "created_at": "ISO8601",
      "updated_at": "ISO8601",
      "is_archived": false
    }

**Media:**

    {
      "media_id": "uuid",
      "name": "string (unique)",
      "description": "string | null",
      "created_at": "ISO8601",
      "updated_at": "ISO8601",
      "is_archived": false
    }

**Image:**

    {
      "image_id": "uuid",
      "strain": "string",
      "species_id": "uuid (FK)",
      "media_id": "uuid (FK)",
      "file_path": "string",
      "segments": [{"segment_index": int, "bbox": {...}, "crop_path": "string"}],
      "data_update_status": "current | updated_requires_reindex | archived",
      "indexed_in_qdrant": false,
      "created_at": "ISO8601",
      "updated_at": "ISO8601"
    }

## Acceptance Criteria

- [ ] Create/update/archive/restore Species with unique name validation
- [ ] Create/update/archive/restore Media with unique name validation
- [ ] Strain handled as image metadata/dataset entity
- [ ] Index new data with required Species, strain, and Media metadata
- [ ] Batch indexing with Species metadata in folder structure
- [ ] Accepted contribution feedback becomes pending reference data before indexing
- [ ] Data Owner dataset browser supports search/filter/group by strain, Media, Species
- [ ] Data Owner can edit image metadata and bounding boxes
- [ ] Edits mark item `updated_requires_reindex`
- [ ] Archive/restore only; no permanent delete
- [ ] Archived data excluded from retrieval/indexing
- [ ] Audit log of all dataset and metadata operations

## Dependencies

- 01-image-input.md (shares upload UI)
- 02-segmentation.md (bounding-box review)
- 05-feedback-pipeline.md (accepted feedback feeds pending data/corrections)
- 07-training-observation.md (Qdrant re-index and external retraining warning)
- 08-roles-and-permissions.md (Data Owner access)
- ../SRS.md UC-004, UC-005, UC-007
