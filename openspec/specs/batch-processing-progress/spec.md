# Batch Processing Progress

## Purpose

Define the progress-aware batch upload, per-image segmentation, per-strain confirmation, and per-strain feature extraction workflow for indexing new image data.

## Requirements

### Requirement: Segmentation errors are diagnosable and isolated
The backend SHALL handle segmentation failures as explicit per-image failures with a safe error message and SHALL NOT return a generic Internal Server Error for known invalid image, model, or artifact states.

#### Scenario: Invalid image fails one image
- **WHEN** a batch contains an image that segmentation cannot decode
- **THEN** that image is marked failed with an error and other uploaded images continue processing

#### Scenario: Segmentation regression is covered
- **WHEN** the previously failing segmentation path is exercised by automated tests
- **THEN** the test asserts a non-500 response or per-image failure state

### Requirement: Upload progress is visible per file
The system SHALL expose and render upload progress as uploaded file count over total file count, and SHALL append each successfully uploaded image to the uploaded list immediately.

#### Scenario: File upload succeeds
- **WHEN** one file in a multi-file batch uploads successfully
- **THEN** the uploaded count increments and that file appears immediately in the uploaded list

#### Scenario: Pending file remains dimmed
- **WHEN** a file has not uploaded successfully yet
- **THEN** the frontend renders that file at 50% opacity while successfully uploaded files render fully visible

### Requirement: Segmentation starts after each successful upload
The backend SHALL schedule segmentation for each image immediately after that image uploads successfully, using bounded concurrent processing.

#### Scenario: First image uploads before batch completes
- **WHEN** the first image in a batch uploads successfully and later images are still uploading
- **THEN** segmentation starts for the first image without waiting for the full batch upload to finish

#### Scenario: Concurrency is bounded
- **WHEN** many images are uploaded in a batch
- **THEN** segmentation runs no more than the configured concurrent image-processing limit at one time

### Requirement: Processing progress is exposed for each long-running stage
The system SHALL expose upload, segmentation, and feature extraction progress as completed count, total count, and percentage where a total is known.

#### Scenario: Segmentation progress updates
- **WHEN** two of five images finish segmentation
- **THEN** the batch progress reports `2/5` segmented images and `40%` segmentation progress

#### Scenario: Feature extraction progress updates
- **WHEN** feature extraction completes for one of four images in a confirmed strain
- **THEN** the strain progress reports `1/4` extracted images and `25%` feature extraction progress

### Requirement: Segment confirmation is per strain
The frontend SHALL allow users to confirm segments for one strain at a time instead of requiring all strains to be confirmed at once.

#### Scenario: Confirm one strain
- **WHEN** the user confirms all segments for the active strain
- **THEN** that strain is marked confirmed and unconfirmed strains remain editable

#### Scenario: Confirmation button shows strain progress
- **WHEN** one of three strains has been confirmed
- **THEN** the confirmation button or adjacent progress label shows `1/3` strains confirmed

### Requirement: Feature extraction starts after strain confirmation
The backend SHALL start feature extraction immediately for a strain after all segments in that strain are confirmed.

#### Scenario: Confirmed strain starts extraction
- **WHEN** the user confirms all segments for a strain
- **THEN** feature extraction starts for images in that strain without waiting for other strains

#### Scenario: UI advances to next strain
- **WHEN** the active strain is confirmed and another unconfirmed strain exists
- **THEN** the frontend moves focus to the next strain tab

### Requirement: Validation covers the full workflow
The change SHALL include automated and manual validation for backend behavior, frontend rendering, integration flow, e2e flow, and browser-based manual workflow.

#### Scenario: Automated tests cover progress workflow
- **WHEN** the test suite runs
- **THEN** it includes tests for segmentation failure handling, per-file upload progress, per-image segmentation scheduling, per-strain confirmation, and feature extraction progress

#### Scenario: Manual browser test is recorded
- **WHEN** implementation is complete
- **THEN** an agent-browser manual test records the batch upload, segmentation confirmation, and feature extraction progress journey
