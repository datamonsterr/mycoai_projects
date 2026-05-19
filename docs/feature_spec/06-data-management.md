# Feature Spec: Data Management (CRUD)

## Overview

Data owners manage species, strains, images, and media in the database.
Full CRUD operations with archive/trash and training awareness.

## User Stories

### 1. Index New Data

**As a** data owner
**I want to** upload strain images for known species and index them as new data
**So that I** can expand the species database used by retrieval

**Create Species:**
- Define new species name
- Optional: species description, reference images, taxonomic info
- Species names must be unique (case-insensitive check)
- On creation: species is empty (no strains yet)

**Index Strain Images:**
- Extends retrieve species workflow from 03-retrieval.md
- Additional field: species (dropdown of known species)
- Data owner classifies in advance — bypasses species prediction
- Image goes through upload, AI auto-segmentation, editable bounding boxes, and result review
- Segments are indexed directly into Qdrant with known species label
- Supports batch upload with species column in template.json

### 2. Read

**As a** data owner / researcher
**I want to** filter and browse the database
**So that I** can understand what data exists

**Filters:**
- By strain (text search)
- By species (dropdown)
- By growth medium (checkboxes)
- By date added (date range)
- By data source (curated_primary, incoming_low_quality, user_upload)

**Overview Dashboard:**

| Metric | Description |
|--------|-------------|
| Total images | Count of all images in database |
| Total strains | Distinct strain count |
| Total species | Distinct species count |
| Total media types | Distinct media count |
| Images per species | Pie chart of species distribution |
| Images per medium | Bar chart of medium distribution |
| Learned vs unlearned | How many strains are indexed in Qdrant |

**Charts:**
- Pie chart: species distribution by image count
- Bar chart: images per growth medium
- Timeline: images added over time
- Status: learned (in Qdrant) vs pending (uploaded but not indexed)

### 3. Update

**As a** data owner
**I want to** update species names
**So that I** can correct taxonomic changes

**Behavior:**
- Rename a species: all strains under that species are relabeled
- Triggers re-indexing for all affected Qdrant points
- Warning: "Renaming will require re-indexing N strains. Proceed?"
- Old species name is soft-deleted (retained in archive)
- Update is atomic: all strains update or none

**Open Question:** Does updating a species name require full re-training
of the deep learning models, or is it sufficient to relabel and re-index
in Qdrant? (See 07-training-observation.md)

### 4. Delete / Archive

**As a** data owner
**I want to** remove incorrect or obsolete data
**So that I** keep the database clean

**Archive (soft delete):**
- Delete moves data to trash/archive — not permanently removed
- Archived data is excluded from Qdrant queries
- Archived data is excluded from training data
- User sees warning: "Archiving N strains. Models must be retrained
  for changes to take effect. [Continue] [Cancel]"
- Archive preserves: images, metadata, timestamps

**Trash Management:**
- View all archived items
- Restore: move back to active (re-index into Qdrant)
- Permanent delete: remove files and database records entirely
- "Empty trash" with confirmation dialog
- Data owner can hit "Retrain" when enough data has been archived

**Retrain Trigger:**
- After significant archiving, data owner manually triggers re-training
- System shows count of archived items since last training
- "Retrain now" button (see 07-training-observation.md)

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

**Strain:**

    {
      "strain_id": "uuid",
      "name": "string",
      "species_id": "uuid (FK)",
      "created_at": "ISO8601",
      "is_archived": false,
      "source": "curated_primary | incoming_low_quality | user_upload"
    }

**Image:**

    {
      "image_id": "uuid",
      "strain_id": "uuid (FK)",
      "media": "string (enum)",
      "file_path": "string",
      "segments": [{"segment_index": int, "bbox": {...}, "crop_path": "string"}],
      "indexed_in_qdrant": false,
      "created_at": "ISO8601",
      "is_archived": false
    }

## Acceptance Criteria

- [ ] Create species with unique name validation
- [ ] Create strain+image with direct species link
- [ ] Batch upload with species classification
- [ ] Filterable database browser (strain, species, media, date, source)
- [ ] Overview dashboard with counts and charts
- [ ] Species rename with bulk relabeling
- [ ] Soft delete (archive) with restore capability
- [ ] Trash management (view, restore, permanent delete, empty)
- [ ] Retrain warning on archive
- [ ] Audit log of all CRUD operations

## Dependencies

- 01-image-input.md (shares upload UI for direct-link creation)
- 05-feedback-pipeline.md (feeds accepted corrections into updates)
- 07-training-observation.md (retrain trigger)
- 08-roles-and-permissions.md (data owner vs normal user)
