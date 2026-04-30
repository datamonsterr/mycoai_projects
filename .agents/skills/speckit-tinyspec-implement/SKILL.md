---
name: speckit-tinyspec-implement
description: Implement a small change from its tinyspec file
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: tinyspec:commands/implement.md
---

# TinySpec Implement

Implement a small change from `specs/tiny/*.md`.

## Steps

1. Locate requested tinyspec or newest file in `specs/tiny/`.
2. Read context, requirements, plan, tasks, done criteria.
3. Read listed context files.
4. Execute tasks in order and mark complete.
5. Run relevant repo checks.
6. Set status done and report modified files/checks.

## Rules

- Follow tinyspec exactly.
- Stop on ambiguity or scope creep.
- Match existing code patterns.