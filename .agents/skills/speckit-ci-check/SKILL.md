---
name: speckit-ci-check
description: Run all spec compliance checks and report pass/fail status for CI pipelines
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: ci-guard:commands/check.md
---

# Spec Compliance Check

Run read-only checks for spec artifacts, completeness, task completion, quick spec-code alignment, and drift. Use `$ARGUMENTS` for scope, threshold, base branch, or output format.

## Steps

1. Confirm git repo and `.specify/` exist.
2. Find active feature artifacts (`spec.md`, `plan.md`, `tasks.md`) and `.speckit-ci.yml` if present.
3. Check required sections: spec requirements/success criteria, plan summary/technical context, tasks phases.
4. Count `tasks.md` checkboxes and compare with configured/default threshold.
5. Compare requirements with changed files from base branch (`main` unless configured).
6. Output a compact table plus recommended CI exit code.

## Rules

- Read-only.
- Deterministic.
- Cite file paths for every fail/warn.
- Default: fail missing `spec.md`; warn missing `plan.md`/`tasks.md`; task threshold 100%.