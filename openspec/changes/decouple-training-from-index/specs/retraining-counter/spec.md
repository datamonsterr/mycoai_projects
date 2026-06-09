## ADDED Requirements

### Requirement: System tracks retraining-relevant changes
The system SHALL maintain an aggregate counter tracking net training-relevant changes since the last acknowledged model training.

#### Scenario: Counter increments on new image ingestion
- **WHEN** a new image is ingested into the reference dataset (via batch upload or index workflow)
- **THEN** the `images_added` counter field SHALL increment by 1

#### Scenario: Counter increments on bounding box correction
- **WHEN** a Data Owner corrects an image's bounding box
- **THEN** the `bbox_corrections` counter field SHALL increment by 1

#### Scenario: Counter increments on image archive
- **WHEN** an image is archived
- **THEN** the `items_archived` counter field SHALL increment by 1

#### Scenario: Counter increments on new species creation
- **WHEN** a new Species is added to the catalog
- **THEN** the `species_added` counter field SHALL increment by 1

#### Scenario: Metadata-only changes do not increment counter
- **WHEN** a Data Owner renames a Species or Strain without changing pixel data or bounding boxes
- **THEN** the retraining counter SHALL NOT increment

#### Scenario: Wrong-prediction feedback acceptance does not increment counter
- **WHEN** feedback of type `wrong_prediction` is accepted and species metadata is corrected
- **THEN** the retraining counter SHALL NOT increment (metadata change only)

### Requirement: Retraining warning activates above threshold
The system SHALL display a retraining warning when the total retraining counter exceeds a configurable threshold.

#### Scenario: Warning shown when threshold exceeded
- **WHEN** `images_added + bbox_corrections + items_archived + species_added` exceeds the configured threshold
- **THEN** the Dashboard SHALL display a retraining warning with guidance and YOLO export link

#### Scenario: Warning not shown below threshold
- **WHEN** the total counter is at or below the threshold
- **THEN** no retraining warning is displayed

#### Scenario: Warning persists across page loads
- **WHEN** the counter exceeds threshold
- **THEN** the warning SHALL appear on every Dashboard load until the counter is reset

### Requirement: Data Owner acknowledges training completion
The system SHALL allow a Data Owner to reset the retraining counter after external training is completed.

#### Scenario: Reset counter on acknowledgment
- **WHEN** Data Owner clicks "Training Complete" button and confirms
- **THEN** all counter fields SHALL reset to 0 and `last_reset_at` SHALL update to current timestamp

#### Scenario: Non-owner cannot reset counter
- **WHEN** a User (not Data Owner) attempts to reset the counter
- **THEN** system returns 403 Forbidden

### Requirement: Counter state is persisted
The retraining counter SHALL survive application restarts.

#### Scenario: Counter survives restart
- **WHEN** the application restarts
- **THEN** the retraining counter SHALL retain its pre-restart values

### Requirement: Threshold is configurable
The retraining warning threshold SHALL be configurable.

#### Scenario: Default threshold
- **WHEN** no threshold is explicitly configured
- **THEN** the default threshold SHALL be 20

#### Scenario: Custom threshold via configuration
- **WHEN** `RETRAINING_WARNING_THRESHOLD` environment variable is set to 50
- **THEN** the warning SHALL activate when the total counter exceeds 50
