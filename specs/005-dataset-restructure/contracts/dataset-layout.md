# Dataset Layout Contract

## Goal
Define canonical filesystem and metadata contract after dataset restructure so all fungal-cv-qdrant preparation, retrieval, training, visualization, and sync workflows resolve dataset artifacts consistently.

**Bugfix**: 2026-05-07 — BUG-001: added ob/rev leaf directories, `segments/` per leaf with 1-indexed naming, removed per-image `item.json` in favor of consolidated array, added letter-range folder skip rule.

## 1. Source Collections

The dataset root contains named source collections for raw inputs. Each source collection:
- represents one provenance/quality class
- remains source-only
- is not used as derived artifact storage

Example shape:

```text
Dataset/
├── curated_primary/               # Renamed from Dataset/original/
│   └── {species}/{strain}/        # {environment}_{angle}.{ext} images
├── incoming_low_quality/           # Renamed from Dataset/new_data/
│   └── {letter-range}/            # Skip: D - L, M - R, S - Z (grouping only)
│       └── {species}/
│           └── {strain}/
│               └── {environment}_{angle}.{ext}    # source images
├── curated_primary_metadata.json   # Consolidated items array
├── incoming_low_quality_metadata.json
└── strain_to_specy.csv
```

## 2. Canonical Derived Hierarchy

Prepared outputs live in one canonical hierarchy organized by species, strain, and environment.

```text
Dataset/
└── prepared/
    └── {species}/
        └── {strain}/
            └── {environment}/
                └── {angle}/                    # ob or rev
                    ├── source.jpg
                    ├── prepared.jpg
                    ├── segments/
                    │   ├── segment_1.jpg
                    │   ├── segment_2.jpg
                    │   └── segment_3.jpg
                    ├── bbox_kmeans.jpg
                    ├── bbox_contour.jpg
                    ├── pipeline_kmeans.jpg
                    └── pipeline_contour.jpg
```

Item metadata lives in `Dataset/{collection}_metadata.json` — one consolidated array per source collection, not per-image `item.json`.

## 3. Naming Rules

- Same parent image shares same leaf directory (species/strain/env/angle).
- Segment filenames are `segment_1.jpg`, `segment_2.jpg`, … — 1-indexed, no method prefix, stored in `segments/` per leaf.
- Angles `ob` and `rev` are leaf directory names, not part of filenames.
- Letter-range grouping folders (`D - L`, `M - R`, `S - Z`) are traversed transparently; never treated as species/strain labels.
- Unknown parsed metadata must still produce deterministic paths under fallback labels.

## 4. Metadata Contract

Retained metadata is path-authoritative, stored as one consolidated JSON array per source collection at `Dataset/{collection}_metadata.json`.

### Item record (per-array entry)
Minimum fields:
- `item_id`: UUID5 from stable source path components
- `source_collection`: `curated_primary` or `incoming_low_quality`
- `instance_info`: `{species, strain, environment, angle}` (flat)
- `paths`: `{source, prepared, segments: [str, ...], bbox_kmeans, bbox_contour, pipeline_kmeans, pipeline_contour}`
- `segmentation`: `{kmeans: [{x, y, w, h}, ...], contour: [{x, y, w, h}, ...]}`
- `parse_status`: `parsed` or `fallback`
- `source_filename`

### Per-leaf segments
Each `ob/` or `rev/` leaf directory contains `segments/segment_1.jpg`, `segment_2.jpg`, … Paths stored in `paths.segments`.

## 5. Consumer Rules

- Consumers MUST read item records from `Dataset/{collection}_metadata.json` arrays.
- Consumers MUST use `paths.segments[n]` for segment image paths — no synthetic `Dataset/segmented_image/{id}.jpg`.
- Bbox coordinates come from `segmentation.{method}[index]`.
- Consumers MUST select segmentation method explicitly (e.g. `segmentation.kmeans`) rather than assuming method-specific directory names.

## 6. Removed Legacy Outputs

These are removed from canonical generation flow:
- `Dataset/full_image/`
- `Dataset/segmented_image/`
- duplicate metadata whose only purpose was to support flat path reconstruction

## 7. Compatibility Expectations

- Retrieval holdout, feature extraction, Qdrant upload, and training must continue to work after switching to metadata-driven path lookup.
- Sync examples and scopes must reference source collections and canonical prepared hierarchy only.
