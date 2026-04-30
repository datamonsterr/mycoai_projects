---
name: speckit-tinyspec-create
description: Generate a single lightweight spec file for small changes
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: tinyspec:commands/create.md
---

# TinySpec Create

Create one concise spec at `specs/tiny/{feature-name}.md` for small tasks.

## Steps

1. Verify `.specify/` and git repo.
2. Assess scope: good fit means 1-5 files, under ~1 hour, low risk.
3. Identify affected/context/test files.
4. Write tinyspec under 80 lines: What, Context, Requirements, Plan, Tasks, Done When.
5. Report file path and next step.

## Rules

- One file only.
- Concrete file refs.
- Testable requirements.
- If scope grows, recommend full `/speckit.specify`.