---
description: Run all fungal-cv-qdrant experiment package tests and lint checks
agent: test-runner
---

Run the full test and lint suite for the fungal-cv-qdrant experiment packages:

1. Run all pytest tests: `uv --directory research run pytest tests/ -q`
2. Run ruff lint on all experiment packages: `uv --directory research run ruff check src/experiments/`
3. Report: PASS if both exit 0, FAIL with grouped error output otherwise
