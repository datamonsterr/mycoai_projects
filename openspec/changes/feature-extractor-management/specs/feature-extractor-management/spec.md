## ADDED Requirements

### Requirement: Feature Extractor dashboard
The system SHALL allow Data Owners to view the active Feature Extractor, Candidate Extractors, version history, latest fixed-set evaluation metrics, promotion status, rollback availability, and index compatibility status.

#### Scenario: Data Owner views extractor dashboard
- **WHEN** Data Owner opens Feature Extractor Management
- **THEN** system shows active extractor version, candidate versions, previous versions, latest evaluation metrics, and whether the current Qdrant index is compatible with the active extractor

### Requirement: Candidate Extractor upload and validation
The system SHALL allow Data Owners to upload a Candidate Extractor artifact with version metadata and SHALL validate artifact format, extractor name, vector dimension, dependency compatibility, and fixed evaluation set compatibility before assessment.

#### Scenario: Valid Candidate Extractor upload
- **WHEN** Data Owner uploads a compatible Candidate Extractor artifact with valid metadata
- **THEN** system stores the artifact as a Candidate Extractor and marks it ready for evaluation

#### Scenario: Invalid Candidate Extractor upload
- **WHEN** Data Owner uploads an artifact with missing metadata, incompatible vector dimension, or unsupported format
- **THEN** system rejects the upload and returns a structured validation error

### Requirement: Candidate Extractor fixed-set assessment
The system SHALL evaluate each Candidate Extractor on a fixed evaluation set and compare its metrics with the current active Feature Extractor before promotion.

#### Scenario: Candidate Extractor evaluation completes
- **WHEN** Data Owner starts Candidate Extractor evaluation
- **THEN** system runs the fixed evaluation set and produces a report with current-vs-candidate metrics and evaluation set identifier

#### Scenario: Evaluation fails
- **WHEN** Candidate Extractor evaluation fails
- **THEN** system records the failure, keeps the Candidate Extractor unpromoted, and shows the error to Data Owner

### Requirement: Manual Candidate Extractor promotion or rejection
The system SHALL require Data Owner manual decision to promote or reject a Candidate Extractor and SHALL never auto-promote an extractor based on metrics alone.

#### Scenario: Data Owner promotes Candidate Extractor
- **WHEN** Data Owner promotes a Candidate Extractor
- **THEN** system marks it as the active Feature Extractor and records an audit event

#### Scenario: Data Owner rejects Candidate Extractor
- **WHEN** Data Owner rejects a Candidate Extractor
- **THEN** system marks it rejected and keeps the current active Feature Extractor unchanged

### Requirement: Promotion marks index compatibility impact
The system SHALL mark the Qdrant index as requiring re-indexing when a promoted Feature Extractor changes the embedding feature space used by stored vectors.

#### Scenario: Promotion changes feature space
- **WHEN** Data Owner promotes a Candidate Extractor with a different feature-space version from the active extractor
- **THEN** system updates the active extractor and marks Qdrant index status as `needs_reindex`

### Requirement: Feature Extractor version history and rollback
The system SHALL preserve Feature Extractor version history and SHALL allow Data Owners to roll back to a previous extractor version, subject to the same index compatibility checks as promotion.

#### Scenario: Data Owner rolls back extractor
- **WHEN** Data Owner selects a previous Feature Extractor version for rollback
- **THEN** system marks that version active, records an audit event, and updates index compatibility status

### Requirement: Retraining signal for extractor lifecycle
The system SHALL show Data Owners retraining signals when accumulated reference-data changes, accepted feedback, archived records, or degraded evaluation metrics indicate that external Feature Extractor retraining may be needed.

#### Scenario: Retraining signal appears
- **WHEN** accumulated changes or evaluation degradation exceed configured thresholds
- **THEN** system shows a retraining recommendation in Feature Extractor Management

### Requirement: Active Feature Extractor governs retrieval
The system SHALL use the globally active Feature Extractor for retrieval and indexing workflows unless a future approved specification introduces per-query extractor selection.

#### Scenario: User retrieves species
- **WHEN** User runs Retrieve Species
- **THEN** system extracts query vectors using the globally active Feature Extractor

#### Scenario: Data Owner indexes data
- **WHEN** Data Owner indexes reference data
- **THEN** system extracts reference vectors using the globally active Feature Extractor
