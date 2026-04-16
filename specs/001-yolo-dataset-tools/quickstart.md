# Quickstart: YOLO Dataset Export and Crop Tools

Run from the monorepo root.

## 1. Export one sample with visual debug assets

```bash
uv --directory fungal-cv-qdrant run python tools/export_yolo_dataset.py \
  --n 1 \
  --output ../Dataset/yolo_curated_smoke \
  --visualize
```

Expected outputs:

- `../Dataset/yolo_curated_smoke/images/`
- `../Dataset/yolo_curated_smoke/labels/`
- `../Dataset/yolo_curated_smoke/hierarchical/`
- `../Dataset/yolo_curated_smoke/metadata.json`
- `../Dataset/yolo_curated_smoke/dataset.yaml`

## 2. Review one hierarchical leaf folder

Inspect the generated leaf folder under:

```text
../Dataset/yolo_curated_smoke/hierarchical/<species>/<strain>/<environment>/
```

Look for:

- resized original image
- bbox visualization image
- optional pipeline visualization image when `--visualize` was enabled

## 3. Crop 512x512 segments from YOLO labels

```bash
uv --directory fungal-cv-qdrant run python tools/crop_yolo_segments.py \
  --input ../Dataset/yolo_curated_smoke \
  --n 1 \
  --output ../Dataset/yolo_crops_smoke
```

Expected outputs:

- one crop per YOLO box under `../Dataset/yolo_crops_smoke/`
- each crop resized to `512x512`

## 4. Run automated checks

```bash
uv --directory fungal-cv-qdrant run pytest
```
