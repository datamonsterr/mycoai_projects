# CLI Contract: YOLO Dataset Export and Crop Tools

## `tools/export_yolo_dataset.py`

### Purpose

Export `Dataset/original/` into a YOLO-compatible curation dataset plus optional hierarchical QC assets.

### Arguments

- `--output <path>`: required output root for the export
- `--n <int>`: optional maximum number of images to process
- `--visualize`: optional flag to emit pipeline visualization assets

### Output Contract

The tool writes:

```text
<output>/
├── images/
│   └── *.jpg
├── labels/
│   └── *.txt
├── hierarchical/
│   └── <species>/<strain>/<environment>/...
├── metadata.json
└── dataset.yaml
```

### Label Contract

Each line in a YOLO label file is:

```text
0 <x_center> <y_center> <width> <height>
```

- `class_id` is always `0`
- coordinates are normalized to the exported image size
- an empty `.txt` file is valid when no boxes are found

### Metadata Contract

`metadata.json` is a list of per-image records containing:

- source file path
- parsed metadata (`species`, `strain`, `environment`, `angle`)
- exported image path
- label path
- bbox pixel coordinates
- visualization paths when present

## `tools/crop_yolo_segments.py`

### Purpose

Read YOLO images and labels, crop each bbox region, and write `512x512` segment images.

### Arguments

- `--input <path>`: required path to the YOLO export root
- `--output <path>`: required output root for segment crops
- `--n <int>`: optional maximum number of source images to process

### Input Contract

- The tool expects `<input>/images/` and `<input>/labels/`
- Each image must have a matching label file by basename

### Output Contract

The tool writes one crop per YOLO bbox.

- crop filenames include the source basename and bbox index
- each crop is resized to `512x512`
- images with empty label files produce no crops and do not fail the run
