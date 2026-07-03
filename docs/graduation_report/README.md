# Graduation Report Workspace

## Purpose

This workspace is source-of-truth for planning, reviewing, validating, and generating the graduation thesis in `graduation_report/`.

## Source-of-truth contract

- `graduation_report/` stores thesis LaTeX source that is edited, committed, and pushed directly.
- `graduation_report/figures/` stores generated artifacts only.
- `docs/graduation_report/code/` stores scripts and diagram/chart/table generators that produce figure assets for `graduation_report/figures/`.
- `research/` stores experiment code, logs, and result artifacts used to regenerate research figures and tables.
- `backend/` and `frontend/` store product implementation that must match thesis claims about actual workflows.

## Required workflow

1. Read `docs/graduation_report/reviews/` before changing thesis content.
2. Read `docs/graduation_report/rules/` before writing or editing any chapter.
3. Read `docs/graduation_report/plans/` to pick current checklist items.
4. Validate claims against `research/`, `backend/`, and `frontend/` before updating prose.
5. Generate or refresh figures from `docs/graduation_report/code/` into `graduation_report/figures/`.
6. Update LaTeX in `graduation_report/`.
7. Compile and audit thesis.
8. Commit and push directly from monorepo root unless user asks otherwise.

## Folder guide

- `reviews/`: strict review findings, weaknesses, mismatches, chapter assessments.
- `plans/`: executable checklists for thesis fixes, implementation fixes, reruns, and validation.
- `rules/`: style, structure, evidence, figure, table, syntax, and honesty rules.
- `code/`: automation for charts, tables, diagrams, and figure regeneration.

## Multi-agent report workflow

Use these report-specific subagents under `.opencode/agents/`.

Configuration note validated against current OpenCode schema:
- report-specialist agents should stay `mode: subagent`
- do not register them as primary agents unless you intentionally want them selectable as top-level chat agents
- `mcp.context7` is correctly modeled as remote MCP config in `.opencode/opencode.json`

Use these report-specific subagents under `.opencode/agents/`:

1. `report-orchestrator` — coordinates thesis workflow and delegates specialist checks.
2. `report-auditor` — strict academic review against docs/rules and code/result truth.
3. `report-research-sync` — validates `research/` outputs and maps stale assets.
4. `report-figure-builder` — generates assets from `docs/graduation_report/code/` into `graduation_report/figures/`.
5. `report-product-validator` — checks thesis claims against `backend/` and `frontend/` implementation and tests.
6. `report-writer` — rewrites chapter prose in `graduation_report/Chapter/`.
7. `report-latex-qa` — compiles and audits LaTeX output.

## Figure generation rule

Do not manually edit generated chart/table/diagram outputs inside `graduation_report/figures/` unless the output format itself requires a final LaTeX-only adjustment. Preferred fix path:

1. update generator source in `docs/graduation_report/code/`
2. rerun generator
3. verify output in `graduation_report/figures/`
4. reference asset from LaTeX

## Commit rule

All accepted thesis-source changes should land in `graduation_report/` and be committed/pushed directly. Supporting review/plan/rule/code docs live under `docs/graduation_report/` and should evolve alongside the thesis.
