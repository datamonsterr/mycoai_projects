<!-- spec: synced 2026-05-11T04:02:09Z from feature_spec/04-visualization.md -->

# Feature Spec: Results Visualization

## Overview

Display retrieval results to the user. Phase 1 implements a ranked list with
detail drill-down per media. Phase 2 adds an interactive KNN graph
visualization.

## Phase 1: Ranked Results List

### User Story

**As a** researcher
**I want** to see species predictions ranked by confidence
**So that** I can quickly identify the most likely species

**Behavior:**
- Results displayed as a ranked table:
  - Rank (1, 2, 3...)
  - Species name
  - Confidence score (0.00-1.00)
  - Color-coded confidence bar
- Click a species row to expand KNN detail:
  - For each query media, show the top-k neighbor images with:
    - Neighbor image thumbnail
    - Neighbor species and strain
    - Cosine similarity score
    - Growth medium
- Sortable by rank, score, or species name
- Export results as CSV

### Visual Design

- Table with alternating row colors
- Confidence score shown as a horizontal bar (green = high, yellow = mid,
  red = low)
- Neighbor detail in an expandable accordion below each species row
- Neighbor thumbnails in a horizontal scrollable row
- Each thumbnail clickable to open full image in a lightbox

## Phase 2: KNN Graph Visualization

### User Story

**As a** researcher
**I want** to see the KNN retrieval as an interactive graph
**So that** I can explore relationships between query and database strains

**Behavior:**
- Graph nodes: query strain (center) + neighbor strains
- Edges: KNN connections weighted by cosine similarity
- Configurable:
  - k (number of neighbors to show, default 5)
  - Weighted vs uni edges
- Node size proportional to number of connections
- Edge thickness proportional to similarity score
- Node color by species
- Hover: show strain name + species + similarity score
- Click: expand neighbor details
- Pan and zoom support

### Graph Layout

- Force-directed layout with query strain at center
- Species as distinct color palette (5 species = 5 colors minimum)
- Legend showing species-to-color mapping
- Responsive canvas that fills available space

## Acceptance Criteria

### Phase 1
- [x] Ranked results table with species, score, rank
- [x] Confidence bar visualization per species
- [x] Expandable per-media KNN neighbor detail
- [x] Neighbor thumbnails with similarity scores
- [x] CSV export of results
- [x] Sortable columns

### Phase 2
- [x] Interactive force-directed graph
- [x] Configurable k slider on the graph
- [x] Weighted/uni toggle
- [x] Species-based node coloring with legend
- [x] Pan, zoom, hover, click interactions
- [x] Graph updates in real-time when k or strategy changes

## Dependencies

- 03-retrieval.md (provides ranked results + KNN details)
- 05-feedback-pipeline.md (may receive feedback from this view)
