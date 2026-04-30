---
name: speckit-tinyspec-classify
description: Classify task complexity and recommend TinySpec or full SDD
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: github-spec-kit
  source: tinyspec:commands/classify.md
---

# TinySpec Classify

Recommend lightweight TinySpec or full SDD.

## Signals

TinySpec: 1-5 files, 1-8 tasks, low risk, single component/endpoint/config/bugfix.
Full SDD: multi-module, architecture, schema, new service, cross-cutting, unknown scope.

## Output

Compact table: task, complexity, estimated files, estimated tasks, risk, recommendation.

## Rules

- Read-only.
- Default to TinySpec when small/medium borderline.
- Explain reason briefly.