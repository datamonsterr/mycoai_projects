---
name: speckit-ci-guard-report
description: Generate a machine-readable spec compliance report with requirement coverage
  metrics
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: ci-guard:commands/report.md
---

# Spec Compliance Report

Produce markdown or JSON requirement traceability: requirements, code evidence, tests, gaps, task phase summary.

## Steps

1. Read active `spec.md`, plus `plan.md`/`tasks.md` if present.
2. Extract stable REQ-001 style IDs from requirements and success criteria.
3. Map each requirement to changed/source files and tests with file:line evidence.
4. Calculate implemented/tested/covered percentages.
5. Output traceability matrix and gaps.

## Rules

- Read-only.
- Every claim cites file paths.
- Default output: compact markdown unless `$ARGUMENTS` requests JSON.