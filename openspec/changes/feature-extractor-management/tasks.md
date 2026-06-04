## 1. Domain Language and SRS

- [ ] 1.1 Update `CONTEXT.md` to add Feature Extractor, Candidate Extractor, and Model definitions with avoided terms.
- [ ] 1.2 Update `CONTEXT.md` relationships so Data Owner manages Candidate Extractors and active Feature Extractor governs retrieval/indexing.
- [ ] 1.3 Update `docs/SRS.md` domain language table to replace Candidate Model with Candidate Extractor and add Feature Extractor.
- [ ] 1.4 Update `docs/SRS.md` use case diagram to add UC-FEX-01 Manage Feature Extractors and remove extractor lifecycle from UC-MODEL-01.
- [ ] 1.5 Add UC-FEX-01 Manage Feature Extractors use case specification with flow tables, data table, and notes.
- [ ] 1.6 Rewrite UC-MODEL-01 so it covers Qdrant re-indexing and external retraining guidance only.
- [ ] 1.7 Rename Candidate Model references to Candidate Extractor in SRS functional requirements, non-functional requirements, rejections, and version history.
- [ ] 1.8 Add FRs for Feature Extractor dashboard, Candidate Extractor upload/validation, fixed-set evaluation, manual promotion/rejection, version history/rollback, retraining signal, and global active extractor behavior.

## 2. Feature Specs

- [ ] 2.1 Update `docs/feature_spec/07-training-observation.md` to split Feature Extractor Management from Qdrant index maintenance.
- [ ] 2.2 Add Feature Extractor dashboard behavior: active extractor, candidates, previous versions, metrics, and index compatibility.
- [ ] 2.3 Add Candidate Extractor upload, validation, evaluation, comparison, manual promotion/rejection, rollback, and audit behavior.
- [ ] 2.4 Update retrieval feature spec to state retrieval uses globally active Feature Extractor with no User-selectable extractor for MVP.
- [ ] 2.5 Update data-management feature spec to state indexing extracts reference vectors using globally active Feature Extractor.
- [ ] 2.6 Update roles-and-permissions feature spec so only Data Owner can manage Feature Extractors.

## 3. Technical Specs

- [ ] 3.1 Update `docs/technical_spec/10-training-pipeline.md` terminology from Candidate Model to Candidate Extractor.
- [ ] 3.2 Split API shape into index endpoints and extractor lifecycle endpoints.
- [ ] 3.3 Specify Candidate Extractor metadata validation fields: extractor name, version, artifact format, vector dimension, feature-space version, evaluation-set compatibility.
- [ ] 3.4 Document promotion impact: active extractor changes SHALL mark Qdrant index `needs_reindex` when feature-space version changes.
- [ ] 3.5 Document version history and rollback behavior with audit logging and index compatibility checks.
- [ ] 3.6 Document external retraining guidance as guidance-only with no in-system deep retraining endpoint.

## 4. Cross-References and Consistency

- [ ] 4.1 Update all docs cross-references from UC-MODEL-01 extractor lifecycle to UC-FEX-01.
- [ ] 4.2 Verify no user-facing docs use "upload deep learning model" as top-level capability; it must be described as Candidate Extractor upload.
- [ ] 4.3 Verify "Model" remains only as umbrella/technical term and not the lifecycle capability label.
- [ ] 4.4 Verify SRS IDs match across use case specs, feature specs, technical specs, and diagram.

## 5. Validation

- [ ] 5.1 Run grep checks for stale `Candidate Model`, `upload deep learning model`, and old UC references.
- [ ] 5.2 Validate Markdown tables render correctly in `docs/SRS.md`.
- [ ] 5.3 Confirm UC-FEX-01 references fungal-cv-qdrant extractor evidence without implying direct imports into product repos.
- [ ] 5.4 Run `openspec status --change feature-extractor-management` and confirm change is apply-ready.
