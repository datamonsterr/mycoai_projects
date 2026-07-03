# Thesis Writing Rules

## Rule 1 — Docs-first workflow

Before editing `graduation_report/`, read:
1. `docs/graduation_report/reviews/`
2. `docs/graduation_report/plans/`
3. `docs/graduation_report/rules/`

## Rule 2 — Claim honesty

Every implementation claim must be classified as one of:
- implemented and tested
- implemented but partially tested
- prototype/scaffold
- planned future work

Never present prototype or scaffold as fully implemented workflow.

## Rule 3 — Figures are evidence, not decoration

Every figure must have:
1. a lead-in sentence before it
2. a caption that defines short labels if needed
3. post-figure interpretation stating what finding it supports
4. a downstream decision or implication when relevant

## Rule 4 — Tables must earn their space

Keep a table only if it does one of:
- compares alternatives
- summarizes reproducible metrics
- clarifies architecture or contracts not better shown in prose
- documents final selected settings with justified reasons

## Rule 5 — Prefer academic labels over code identifiers

Main prose should prefer human-readable names. Raw code identifiers may appear in method tables, appendices, chart legends, or reproducibility notes.

## Rule 6 — Methodology first, interpretation later

Methodology sections define how the system works. Result claims, comparative wording, and performance judgments belong in experiment/result sections.

## Rule 7 — Latest validated result only

If a claim depends on metric values, it must come from latest rerun or validated artifact tracked by current workflow.

## Rule 8 — Product screenshots need functional purpose

Do not include UI screenshots just to prove a page exists. Each screenshot must support a use case, requirement, or implementation decision.
