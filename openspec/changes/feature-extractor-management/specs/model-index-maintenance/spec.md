## ADDED Requirements

### Requirement: Qdrant re-indexing remains in-system
The system SHALL allow Data Owners to trigger Qdrant re-indexing for changed active reference data, metadata edits, bounding-box edits, archive/restore events, and accepted feedback or contribution changes.

#### Scenario: Data Owner triggers re-index
- **WHEN** Data Owner confirms Qdrant re-indexing
- **THEN** system re-extracts features for active changed segments with the active Feature Extractor and updates Qdrant points

### Requirement: Archived data exclusion during re-index
The system SHALL exclude archived dataset records from Qdrant retrieval and re-indexing.

#### Scenario: Archived item exists during re-index
- **WHEN** Qdrant re-indexing runs with archived dataset items present
- **THEN** system excludes archived items from active Qdrant retrieval and preserves their archive state

### Requirement: Re-index status and audit logging
The system SHALL track Qdrant index status and SHALL audit all Data Owner re-index actions.

#### Scenario: Re-index completes
- **WHEN** Qdrant re-indexing finishes successfully
- **THEN** system marks affected data current, updates index status, and records an audit event

### Requirement: External retraining guidance only
The system SHALL provide Data Owners with Python guidance for external Feature Extractor retraining and SHALL NOT provide an in-system deep retraining trigger.

#### Scenario: Retraining guidance requested
- **WHEN** Data Owner reviews external retraining guidance
- **THEN** system shows dataset download, external retraining, and Candidate Extractor upload guidance without starting any retraining job

### Requirement: Feature Extractor lifecycle excluded from index maintenance
The system SHALL handle Candidate Extractor upload, validation, evaluation, promotion, rejection, version history, and rollback through Feature Extractor Management instead of Qdrant index maintenance.

#### Scenario: Data Owner wants to upload extractor
- **WHEN** Data Owner initiates Candidate Extractor upload from index maintenance context
- **THEN** system routes Data Owner to UC-FEX-01 Manage Feature Extractors
