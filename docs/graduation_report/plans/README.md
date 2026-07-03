# Graduation Report Fix Plan

## Phase 0 — Ground truth and workflow control

- [ ] Read `docs/graduation_report/reviews/` before thesis edits.
- [ ] Read `docs/graduation_report/rules/` before thesis edits.
- [ ] Inventory thesis claims that require backing from `research/`, `backend/`, `frontend/`.
- [ ] Mark each claim as implemented, partially implemented, planned, or unsupported.
- [ ] Freeze unsupported claims until implemented or downgraded.

## Phase 1 — Backend actual workflow

- [ ] Remove or replace stub/mock training lifecycle endpoints in `backend/` where thesis claims require real workflow.
- [ ] Implement real candidate-model upload/promotion flow or downgrade thesis claims.
- [ ] Add backend tests for retrieval, segmentation review, feedback, indexing, training lifecycle, role permissions.
- [ ] Run backend checks: `uv --directory backend run ruff check`, `uv --directory backend run mypy`, `uv --directory backend run pytest`.
- [ ] Record remaining backend gaps that thesis must not overclaim.

## Phase 2 — Frontend actual workflow

- [ ] Remove mock-data dependency from user-facing thesis-relevant paths.
- [ ] Ensure retrieval, segmentation review, feedback, indexing, model/index maintenance use real backend APIs.
- [ ] Add or update frontend tests for thesis-relevant workflows.
- [ ] Add e2e validation for core user journey: login → upload → segmentation review → retrieval results.
- [ ] Run frontend checks: `pnpm --dir frontend lint`, `pnpm --dir frontend typecheck`, `pnpm --dir frontend build`, relevant tests/e2e.
- [ ] Capture screenshots only from real tested workflows.

## Phase 3 — Research rerun and latest results

- [ ] Audit `research/` experiments used by thesis figures and tables.
- [ ] Fix bugs in experiment scripts and asset-generation code.
- [ ] Run latest retrieval, segmentation, cross-validation, threshold, and fine-tuning analyses needed by thesis.
- [ ] Save reproducible output locations for every figure/table claim.
- [ ] Confirm best configuration from latest rerun, not stale report prose.
- [ ] Update mismatch log if results differ from thesis statements.

## Phase 4 — Automated figure/table regeneration

- [ ] For every thesis figure/table under `graduation_report/figures/`, identify owning generator under `docs/graduation_report/code/`.
- [ ] Add missing generators for manual-only assets that should be reproducible.
- [ ] Standardize script inputs/outputs and output paths.
- [ ] Regenerate charts, tables, diagrams automatically from latest validated data.
- [ ] Verify generated files overwrite stale assets in `graduation_report/figures/`.
- [ ] Document command examples in `docs/graduation_report/code/README.md` if needed.

## Phase 5 — Thesis rewrite

- [ ] Rewrite Chapter 1 problem framing and scope.
- [ ] Rewrite Chapter 2 experiment subsections with stronger setup/result/interpretation structure.
- [ ] Rewrite Chapter 3 to separate implemented vs prototype workflows.
- [ ] Add measurable Chapter 4 evaluation.
- [ ] Rewrite Chapter 5 conclusion and future work.
- [ ] Replace raw code-like strategy names in prose with academic labels.

## Phase 6 — Final validation

- [ ] Compile LaTeX and fix blocking errors.
- [ ] Audit numbering, captions, labels, references, glossary, bibliography, and figure paths.
- [ ] Check every figure has lead-in, explicit interpretation, and decision impact.
- [ ] Check every table has purpose and analytical value.
- [ ] Check every implementation claim matches tested code.
- [ ] Commit and push final thesis updates directly.
