# Dataset Layout Contract

## Goal
Define canonical filesystem and metadata contract after dataset restructure so all fungal-cv-qdrant preparation, retrieval, training, visualization, and sync workflows resolve dataset artifacts consistently.

## 1. Source Collections

The dataset root contains named source collections for raw inputs. Each source collection:
- represents one provenance/quality class
- remains source-only
- is not used as derived artifact storage

Example shape:

```text
Dataset/
├── [primary-source-collection]/
└── [incoming-source-collection]/
```

## 2. Canonical Derived Hierarchy

Prepared outputs live in one canonical hierarchy organized by species, strain, and environment.

```text
Dataset/
└── prepared/
    └── {species}/
        └── {strain}/
            └── {environment}/
                └── {image_stem}/
                    ├── source.jpg
                    ├── prepared.jpg
                    ├── segments_kmeans/
                    │   ├── seg_0.jpg
                    │   ├── seg_1.jpg
                    │   └── seg_2.jpg
                    ├── segments_yolo/
                    │   ├── seg_0.jpg
                    │   ├── seg_1.jpg
                    │   └── seg_2.jpg
                    ├── bbox_kmeans.jpg
                    ├── bbox_yolo.jpg
                    ├── pipeline_kmeans.jpg
                    ├── pipeline_yolo.jpg
                    └── item.json
```

## 3. Naming Rules

- Same parent image uses same `{image_stem}` across methods.
- Segment filenames are method-local and index-based.
- `segments_kmeans/` and `segments_yolo/` are reserved names.
- Unknown parsed metadata must still produce deterministic paths under fallback labels.

## 4. Metadata Contract

Retained metadata must be path-authoritative.

### Item record
Minimum fields:
- `item_id`
- `source_collection`
- `species`
- `strain`
- `environment`
- `angle`
- `source_image_path`
- `prepared_image_path`
- `artifact_root`

### Segment record
Minimum fields:
- `segment_id`
- `parent_item_id`
- `method`
- `segment_index`
- `segment_path`
- `species`
- `strain`
- `environment`
- `angle`
- `bbox`

## 5. Consumer Rules

- Consumers MUST NOT assume `Dataset/segmented_image/{id}.jpg`.
- Consumers MUST use metadata-provided segment paths.
- Consumers MUST select segmentation method explicitly or use documented default.
- Visualization helpers MUST load paths from metadata records, not synthetic joins.

## 6. Removed Legacy Outputs

These are removed from canonical generation flow:
- `Dataset/full_image/`
- `Dataset/segmented_image/`
- duplicate metadata whose only purpose was to support flat path reconstruction

## 7. Compatibility Expectations

- Retrieval holdout, feature extraction, Qdrant upload, and training must continue to work after switching to metadata-driven path lookup.
- Sync examples and scopes must reference source collections and canonical prepared hierarchy only.
