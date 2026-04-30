---
name: speckit-ci-guard-gate
description: Configure merge gate rules
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: ci-guard:commands/gate.md
---

# Configure Merge Gates

Create or update `.speckit-ci.yml` for spec compliance gates.

## Steps

1. Read existing `.speckit-ci.yml` if present.
2. Pick profile from `$ARGUMENTS`: strict, moderate default, relaxed, or custom.
3. Write required artifacts, task threshold, drift, test coverage, and branch base settings.
4. Show summary and CI snippet.

## Rules

- If config exists, show proposed diff before overwriting.
- Keep config concise and repo-agnostic.
- Moderate defaults: require `spec.md` + `plan.md`, recommend `tasks.md`, task threshold 80%, drift warn-only.