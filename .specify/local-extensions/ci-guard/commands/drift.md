---
description: "Detect spec-to-code drift"
---

# Spec Drift Detection

Compare spec intent with implementation and report forward/reverse/decision drift.

## Steps

1. Read active `spec.md`, optional `plan.md`/`tasks.md`.
2. Extract requirements, scenarios, success criteria, planned files, decisions.
3. Scan referenced files and current branch diff.
4. Report forward drift (spec missing in code), reverse drift (code not in spec), decision drift.
5. Include drift score and remediation direction.

## Rules

- Read-only.
- Evidence required: file_path:line_number or artifact section.
- Classify severity critical/warn/info.
