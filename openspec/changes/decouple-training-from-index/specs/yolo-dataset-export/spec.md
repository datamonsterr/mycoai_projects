## ADDED Requirements

### Requirement: Data Owner exports active dataset in YOLO format
The system SHALL allow a Data Owner to download the current active reference dataset as a YOLO-format zip archive for external feature-extractor training.

#### Scenario: Export with filters applied
- **WHEN** Data Owner navigates to Dataset Browser, selects filters (species, media, status), and clicks "Export YOLO"
- **THEN** system streams a zip file containing `images/` directory with all matching image files and `labels/` directory with per-image YOLO-format `.txt` label files

#### Scenario: YOLO label format correctness
- **WHEN** a YOLO export is generated
- **THEN** each label file contains one line per segment with format `<class_id> <x_center> <y_center> <width> <height>` normalized to [0,1]

#### Scenario: Species-to-class-index mapping
- **WHEN** a YOLO export is generated
- **THEN** species are consistently mapped to class indices 0..N-1 and a `classes.txt` file is included with one species name per line

#### Scenario: Archived images excluded
- **WHEN** a YOLO export is requested
- **THEN** images with `data_update_status = 'archived'` SHALL be excluded from the export

#### Scenario: Non-owner access denied
- **WHEN** a User (not Data Owner) requests the YOLO export endpoint
- **THEN** system returns 403 Forbidden

#### Scenario: Empty dataset returns valid zip
- **WHEN** filters match zero images
- **THEN** system returns a valid zip containing only `classes.txt` with no image or label files

### Requirement: Export endpoint supports filtering
The YOLO export endpoint SHALL accept query parameters to filter the exported dataset.

#### Scenario: Filter by species
- **WHEN** Data Owner requests export with `?species_id=sp-001`
- **THEN** only images belonging to that species are included

#### Scenario: Filter by media
- **WHEN** Data Owner requests export with `?media_id=m-001`
- **THEN** only images on that media type are included

#### Scenario: Combined filters
- **WHEN** Data Owner requests export with both `?species_id=sp-001&media_id=m-001`
- **THEN** only images matching both filters are included

### Requirement: Export respects data update status filter
The YOLO export SHALL filter by `data_update_status`.

#### Scenario: Export only current-status images
- **WHEN** Data Owner requests export with `?status=current`
- **THEN** only images with `data_update_status = 'current'` are included

#### Scenario: Default excludes archived
- **WHEN** no status filter is provided
- **THEN** images with `data_update_status = 'archived'` are excluded by default
