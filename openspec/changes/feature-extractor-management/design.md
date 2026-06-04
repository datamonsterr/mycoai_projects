## Context

MycoAI Retrieval currently describes "Candidate Model" upload inside UC-MODEL-01 Maintain Model and Index. That use case conflates Qdrant index maintenance with feature extractor lifecycle. The fungal-cv-qdrant experiments already model extractors explicitly through `FeatureExtractor` in `src/experiments/feature_extraction/feature_extractors.py`; `generate_features.py` iterates concrete extractors such as HOG, Gabor, ResNet50, MobileNetV2, EfficientNetB1, and hybrid color-histogram extractors. The monorepo also keeps `species_weights.json`, which weights per-species extractor outputs when combining model results.

The docs should match that domain: a Feature Extractor produces vectors from segmented colony crops, a Candidate Extractor is an uploaded extractor awaiting fixed-set assessment, and Model remains an umbrella term for the architecture + weights artifact. Deep learning model upload is therefore a subset of Feature Extractor Management, not a separate top-level concept.

## Goals / Non-Goals

**Goals:**

- Add UC-FEX-01 Manage Feature Extractors as the authoritative use case for extractor lifecycle.
- Move upload/evaluate/compare/promote/reject/version-history behavior out of UC-MODEL-01.
- Keep UC-MODEL-01 focused on Qdrant re-indexing and retraining guidance.
- Align docs with fungal-cv-qdrant implementation terms and artifacts.
- Preserve globally active extractor behavior for retrieval; Users do not select extractors per query.
- Define how Data Owner decisions promote a Candidate Extractor to the active extractor used by retrieval and indexing.

**Non-Goals:**

- No in-system deep feature-extractor retraining.
- No User-facing extractor selector in UC-RETRIEVE-01.
- No live traffic A/B testing for extractor candidates.
- No immediate backend/frontend implementation in this change proposal.
- No direct import from fungal-cv-qdrant into product repos; product behavior must be reimplemented locally when applied.

## Decisions

### Decision 1: Canonical domain terms

Use three terms:

- **Feature Extractor**: embedding network or algorithm that converts segmented colony crops into vectors.
- **Candidate Extractor**: uploaded extractor version under Data Owner assessment.
- **Model**: umbrella term for architecture + weights artifact.

Alternative considered: keep "Candidate Model" everywhere. Rejected because it hides that the uploaded artifact must be compatible with vector extraction and Qdrant feature-space constraints.

### Decision 2: Split extractor lifecycle from index maintenance

Create **UC-FEX-01 Manage Feature Extractors** for dashboard/status view, Candidate Extractor upload, validation, fixed-set evaluation, comparison, manual promotion/rejection, version history, rollback capability, and retraining/performance degradation signals.

Keep **UC-MODEL-01 Maintain Model and Index** for Qdrant re-index and external retraining guidance only.

Alternative considered: keep UC-MODEL-01 unified and rename internals. Rejected because upload/evaluate/promote is a lifecycle distinct from re-indexing. The split improves testability and prevents "model" from swallowing both extractor and index concepts.

### Decision 3: Global active extractor only

Retrieval uses the globally active extractor version. Data Owners change active extractor through UC-FEX-01 promotion. Users do not select extractor versions per retrieval request.

Alternative considered: per-query extractor selector. Rejected for MVP because extractor versions imply different embedding spaces. Safe per-query selection requires multi-version Qdrant vectors or separate collections, extra UX complexity, and clear compatibility rules.

### Decision 4: Promotion can require re-indexing

Promoting a Candidate Extractor changes the active vector-generation behavior. Existing Qdrant vectors may become incompatible unless regenerated with the promoted extractor. Therefore promotion SHALL mark the Qdrant index as requiring re-index or trigger a guided re-index flow through UC-MODEL-01.

Alternative considered: promote extractor without index impact. Rejected because changing feature space while keeping old vectors can produce invalid KNN results.

### Decision 5: Fixed evaluation set remains MVP assessment method

Candidate Extractors are evaluated on a fixed evaluation set and compared to the current active extractor. Metrics include overall F1 where available, per-Species performance where available, confusion matrix preview where available, and evaluation-set identifier/version.

Alternative considered: live A/B traffic split. Rejected as too complex for current product scope and risky for scientific workflows.

### Decision 6: Version history supports rollback, not deletion

Extractor artifacts and metadata are retained as version history. Previous versions can be selected for rollback by Data Owner, but rollback also requires index compatibility handling through UC-MODEL-01.

Alternative considered: delete rejected or old artifacts. Rejected because auditability and scientific reproducibility require preserving assessment history.

## Risks / Trade-offs

- **Extractor promotion invalidates vector space** → Mark index `needs_reindex` after promotion and route Data Owner to UC-MODEL-01 re-index flow.
- **Term "Model" remains in technical libraries** → Keep Model as umbrella term but require user-facing docs to use Feature Extractor or Candidate Extractor when referring to embedding artifact lifecycle.
- **Fixed evaluation set can become stale** → Store evaluation-set identifier/version in reports and surface retraining/performance degradation signals.
- **Rollback may not be instant** → Treat rollback as changing active extractor plus re-index requirement, not a one-click silent switch.
- **fungal-cv-qdrant implementation uses multiple extractors and weights** → Product docs specify global active extractor for MVP; multi-extractor weighted ensemble remains experimental input unless separately specified.

## Migration Plan

1. Update `CONTEXT.md` terminology.
2. Update `docs/SRS.md`: add UC-FEX-01, rename Candidate Model to Candidate Extractor, update FR/NFRs and diagram.
3. Update `docs/feature_spec/07-training-observation.md`: split extractor management from index maintenance.
4. Update `docs/technical_spec/10-training-pipeline.md`: rename API concepts and document promotion/re-index coupling.
5. Update SRS/feature/technical cross-references to use UC-FEX-01 and scoped UC-MODEL-01.
6. When product implementation begins, reimplement extractor management in backend/frontend without importing fungal-cv-qdrant modules.
