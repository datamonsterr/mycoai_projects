## Why

The SRS uses "model" for two distinct concepts — a Qdrant index state and a feature extractor network — while the fungal-cv-qdrant codebase already treats feature extractors as versioned, swappable artifacts (FeatureExtractor ABC, species_weights.json). The term "upload deep learning model" is a subset of a broader *feature extractor management* lifecycle. Giving extractors their own use case fixes terminology drift, makes the promotion pipeline explicit, and aligns the SRS with the real implementation.

## What Changes

- Define canonical term trio: **Feature Extractor** (embedding network), **Candidate Extractor** (uploaded version under assessment), **Model** (umbrella for architecture + weights artifact)
- New use case **UC-FEX-01 Manage Feature Extractors** covering full extractor lifecycle: dashboard, upload/validate, evaluate/compare, promote/reject, version history/rollback, retraining signal
- **UC-MODEL-01 Maintain Model and Index** descoped to Qdrant re-index + retraining guidance only
- Rename "Candidate Model" → "Candidate Extractor" throughout SRS, CONTEXT.md, feature specs, and technical specs
- FR-028 split into FR-035 through FR-040 for extractor-specific requirements
- Use case diagram updated: UC-FEX-01 added, UC-MODEL-01 edges reduced
- Users always use globally active extractor (no per-query selection); Data Owners control which extractor is active via promotion

## Capabilities

### New Capabilities

- `feature-extractor-management`: Data Owner uploads Candidate Extractors, evaluates against fixed set, compares with current, promotes/rejects, views version history with rollback capability, and receives retraining signals when accumulated data changes degrade extractor performance

### Modified Capabilities

- `model-index-maintenance`: UC-MODEL-01 scope reduced to Qdrant re-indexing and external retraining Python guidance only; extractor lifecycle moves to UC-FEX-01

## Impact

- **SRS.md**: Add UC-FEX-01 spec, update UC-MODEL-01 scope, rename "Candidate Model" everywhere, new FR-035–FR-040, updated use case diagram, new NFR for extractor version retention
- **CONTEXT.md**: Replace "Candidate Model" definition with "Candidate Extractor"; add "Feature Extractor" term
- **docs/feature_spec/07-training-observation.md**: Split into extractor management (new) and index maintenance (existing)
- **docs/technical_spec/10-training-pipeline.md**: API endpoints for extractor upload/evaluate/promote/reject
- **All cross-reference docs**: UC-MODEL-01 → updated scope; new UC-FEX-01 links added
