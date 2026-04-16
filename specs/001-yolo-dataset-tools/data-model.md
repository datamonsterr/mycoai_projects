# Data Model: YOLO Dataset Export and Crop Tools

## SourceImage

- **Description**: One discovered file from `Dataset/original/`.
- **Fields**:
  - `source_path`: absolute or workspace-relative file path
  - `source_filename`: original filename
  - `width`: original width in pixels
  - `height`: original height in pixels
  - `species`: parsed species or `unknown`
  - `strain`: parsed strain or `unknown`
  - `environment`: parsed environment or `unknown`
  - `angle`: parsed angle or `unknown`
  - `sample_id`: stable derived identifier used in output names
- **Validation Rules**:
  - File must be readable by OpenCV
  - `sample_id` must be unique within one export run

## PreprocessResult

- **Description**: Scale-aware preprocessing outputs for one source image.
- **Fields**:
  - `square_image`: center-cropped square source image
  - `resized_image`: curated export image at `3000x3000`
  - `preprocessed_image`: segmentation-ready image
  - `plate_circle`: optional `{center_x, center_y, radius}`
  - `debug_steps`: optional named images for visualization
- **Validation Rules**:
  - `square_image` width must equal height
  - `resized_image` must be exactly `3000x3000`
  - `debug_steps` keys are present only when visualization is enabled

## BoundingBoxProposal

- **Description**: One colony bbox in pixel coordinates on the curated export image.
- **Fields**:
  - `xmin`
  - `ymin`
  - `xmax`
  - `ymax`
  - `source`: `kmeans`
- **Validation Rules**:
  - `0 <= xmin < xmax <= image_width`
  - `0 <= ymin < ymax <= image_height`

## YoloAnnotation

- **Description**: One one-class YOLO label entry derived from a bounding box.
- **Fields**:
  - `class_id`: always `0`
  - `x_center`: normalized float in `[0, 1]`
  - `y_center`: normalized float in `[0, 1]`
  - `width`: normalized float in `(0, 1]`
  - `height`: normalized float in `(0, 1]`
- **Validation Rules**:
  - All normalized values must stay within YOLO bounds
  - Empty label files are valid when no bbox proposals exist

## ExportRecord

- **Description**: One metadata row describing the exported sample.
- **Fields**:
  - `sample_id`
  - `source_path`
  - `image_path`
  - `label_path`
  - `hierarchical_dir`
  - `visualization_paths`
  - `metadata`: `{species, strain, environment, angle}`
  - `bboxes`: list of `BoundingBoxProposal`
- **Relationships**:
  - One `SourceImage` produces one `ExportRecord`
  - One `ExportRecord` may contain zero or more `BoundingBoxProposal` items

## SegmentCrop

- **Description**: One `512x512` crop generated from one YOLO annotation.
- **Fields**:
  - `source_image_path`
  - `source_label_path`
  - `crop_index`
  - `crop_path`
  - `bbox_pixels`
  - `output_size`: always `512x512`
- **Validation Rules**:
  - Crop coordinates must be clamped to the image bounds
  - Output image must be exactly `512x512`

## Relationships Summary

- `SourceImage` -> `PreprocessResult`: one-to-one
- `PreprocessResult` -> `BoundingBoxProposal`: one-to-many
- `BoundingBoxProposal` -> `YoloAnnotation`: one-to-one transform
- `ExportRecord` aggregates one source image plus all derived annotations and assets
- `YoloAnnotation` -> `SegmentCrop`: one-to-one when the crop tool is run
