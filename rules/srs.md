# SRS v2.0.0 Sync Rule

Context: SRS v2.0.0 generated from `docs/SRS.md`, feature/technical specs in `/home/dat/dev/mycoai_projects`.
Mistake: Source docs in `~/dev/mycoai_projects` still use UC-001 format, prose flow bullets, old diagram code, missing UC-PREP-01 spec.
Correct rule: Source docs must match SRS v2.0.0 output — flow tables, UC-{MODULE}-{SEQ} IDs, UC-PREP-01 spec, updated diagram, removed auth includes, no architecture overview in SRS.
Example fix: Apply changes below per file.

## Changes per file

### docs/SRS.md
1. Rename all UC IDs: UC-001→UC-AUTH-01, UC-002→UC-RETRIEVE-01, UC-003→UC-FEEDBACK-01, UC-004→UC-DATA-01, UC-005→UC-META-01, UC-006→UC-AUTH-02, UC-007→UC-DATA-02, UC-008→UC-MODEL-01.
2. Replace prose bullet flow sections (Main flow, Alternative flows, Exception flows) with table format: | Step | Actor | System Response |.
3. Insert UC-PREP-01: Prepare Segmented Images specification between UC-RETRIEVE-01 and UC-FEEDBACK-01 (use content from `output/mycoai_projects/v2/srs-content.md` lines after `### UC-PREP-01`).
4. In UC-RETRIEVE-01 main flow step 5-7, update system/actor descriptions to reference UC-PREP-01 (e.g. "System invokes UC-PREP-01 Prepare Segmented Images to run auto-segmentation").
5. In UC-DATA-01 main flow step 6-7, same reference to UC-PREP-01.
6. Update use case diagram code block: rename `Prepare Segmented\nImages` to `UC-PREP-01\nPrepare Segmented\nImages`, remove all `..> UC_AUTH_01 : <<include>>` lines.
7. Add new FRs: FR-030 (configurable KNN), FR-031 (multi-media queries), FR-032 (results visualization), FR-033 (dataset dashboard), FR-034 (role-based API enforcement).
8. Add new NFRs: NFR-009 to NFR-015 (API error format, async processing, Data Owner constraint, JWT expiry, network security, HTTPS).
9. Remove section 10 (Architecture Overview) — architecture lives in `docs/technical_spec/01-tech-stack.md`.
10. Remove section 9 (Traceability Matrix) — links live in feature/tech spec cross-references.
11. Renumber remaining sections (rejections → 10, version history → 11).
12. Update Version History entry for 2.0.0 with full changelog.
13. Add to UC-RETRIEVE-01 Notes: "Data Owner can also retrieve species through inherited User capabilities."
14. Update UC-DATA-01 Includes field: replace "Prepare Segmented Images" with "UC-PREP-01 Prepare Segmented Images".

### CONTEXT.md
1. Update "Prepare Segmented Images" definition line 77: add "(UC-PREP-01)" suffix to term label.

### docs/feature_spec/03-retrieval.md
1. In user story "Retrieve Species" behavior bullets, update "Auto segment colonies with AI" to reference UC-PREP-01.
2. Update batch alternative flow to invoke UC-PREP-01.

### docs/feature_spec/06-data-management.md
1. Update "Index New Data" behavior bullets to reference UC-PREP-01 in segmentation step.
2. Update batch indexing to invoke UC-PREP-01.

## Verification
- No raw pipe tables rendered as text (all use proper Markdown table syntax)
- UC-{MODULE}-{SEQ} IDs match across specs, diagram, and sequence diagrams
- All main/alt/exception flows use tables, not prose bullets
- No `<<include>>` to UC_AUTH_01 in diagram
- UC-PREP-01 referenced by UC-RETRIEVE-01 and UC-DATA-01
- Architecture Overview and Traceability Matrix removed from SRS.md
- Version history includes 2.0.0 entry dated 2026-06-02
