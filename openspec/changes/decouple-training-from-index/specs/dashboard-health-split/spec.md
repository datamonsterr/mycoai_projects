## ADDED Requirements

### Requirement: Dashboard displays separate index and training health cards
The system SHALL display two independent health cards on the Dashboard and Model Index pages: "Qdrant Index Health" and "Model Training Status".

#### Scenario: Index health card shows re-index metrics
- **WHEN** a Data Owner views the Dashboard
- **THEN** the "Qdrant Index Health" card SHALL display: index status badge, count of items updated since last index, count of items archived, count of feedback accepted, count of contributions accepted, and a "Re-index Qdrant" button

#### Scenario: Training status card shows retraining metrics
- **WHEN** a Data Owner views the Dashboard
- **THEN** the "Model Training Status" card SHALL display: current model version, retraining counter breakdown (images added, bbox corrections, items archived, species added), threshold progress indicator, and when warning is active, guidance text and a "Export YOLO Dataset" link

#### Scenario: Training status card shows no warning below threshold
- **WHEN** the retraining counter is below the threshold
- **THEN** the "Model Training Status" card SHALL show "Model is current" with counter values but no warning styling

#### Scenario: Training status card links to Candidate Model upload
- **WHEN** viewing the "Model Training Status" card
- **THEN** an "Upload Candidate Model" link/button SHALL navigate to the Model Index page

### Requirement: Model Index page reflects decoupled state
The Model Index page SHALL display the same two-card split as the Dashboard.

#### Scenario: Model Index shows re-index card
- **WHEN** a Data Owner navigates to /model
- **THEN** the "Qdrant Index Status" card SHALL be present with current metrics and re-index button

#### Scenario: Model Index shows training card
- **WHEN** a Data Owner navigates to /model
- **THEN** the "Feature Extractor Model" card SHALL be present with retraining counter, guidance dialog, and candidate model management

### Requirement: IndexStatus API returns split response
The GET /api/v1/index/status endpoint SHALL return separate `reindex` and `retraining` objects.

#### Scenario: API response structure
- **WHEN** a Data Owner requests index status
- **THEN** the response SHALL contain `reindex` (with status, items_updated, items_archived, feedback_accepted, contributions_accepted) and `retraining` (with counter fields, threshold, warning_active, last_training_completed_at)

#### Scenario: Frontend types match API shape
- **WHEN** the backend returns the split response
- **THEN** the frontend `IndexStatus` TypeScript type SHALL match the new shape

### Requirement: System never auto-initiates model training
The system SHALL NOT have any code path that automatically triggers deep feature-extractor training.

#### Scenario: No auto-training trigger exists
- **WHEN** any data change occurs (new image, bbox correction, feedback acceptance)
- **THEN** no TrainingJob with `job_type='training'` is created automatically

#### Scenario: TrainingJob model remains for audit only
- **WHEN** external training completes and a model is uploaded as Candidate Model
- **THEN** the TrainingJob model MAY record the upload event but SHALL NOT trigger training execution
