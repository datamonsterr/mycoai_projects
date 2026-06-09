## ADDED Requirements

### Requirement: Per-item re-index tracking via data_update_status
The system SHALL track per-image Qdrant index staleness using the `Image.data_update_status` field, independent of retraining state.

#### Scenario: Status set to current after re-index
- **WHEN** a Qdrant re-index job completes successfully for an image
- **THEN** the image's `data_update_status` SHALL be set to `current`

#### Scenario: Status set to updated_requires_reindex on metadata edit
- **WHEN** a Data Owner edits an image's species or strain metadata
- **THEN** the image's `data_update_status` SHALL be set to `updated_requires_reindex`

#### Scenario: Status set to pending_reindex on accepted wrong-prediction feedback
- **WHEN** feedback of type `wrong_prediction` or `issue` is accepted
- **THEN** the referenced image's `data_update_status` SHALL be set to `pending_reindex`

#### Scenario: Status set to pending_reference on accepted contribution feedback
- **WHEN** feedback of type `contribution` is accepted
- **THEN** the referenced image's `data_update_status` SHALL be set to `pending_reference`

#### Scenario: Status set to archived on archive action
- **WHEN** an image is archived
- **THEN** its `data_update_status` SHALL be set to `archived`

#### Scenario: Re-index warning shown when items need re-index
- **WHEN** any images have `data_update_status` other than `current`
- **THEN** the Dashboard SHALL display a re-index warning with item counts

### Requirement: Re-index is manual, never automatic
The system SHALL NOT automatically trigger Qdrant re-indexing. Only a Data Owner may initiate it.

#### Scenario: Manual trigger only
- **WHEN** re-index warning is active
- **THEN** no re-index job starts until Data Owner clicks "Re-index Qdrant" button

#### Scenario: Re-index endpoint is owner-only
- **WHEN** a User (not Data Owner) calls POST /api/v1/index/reindex
- **THEN** system returns 403 Forbidden

### Requirement: Re-index pre-flight summary
The system SHALL show a pre-flight summary before starting a re-index job.

#### Scenario: Pre-flight dialog shows change breakdown
- **WHEN** Data Owner clicks "Re-index Qdrant"
- **THEN** a dialog appears showing counts of items to re-extract, items to exclude (archived), and feedback-driven updates

#### Scenario: Cancellation supported
- **WHEN** the pre-flight dialog is open
- **THEN** Data Owner can cancel without triggering re-index
