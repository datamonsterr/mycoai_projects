---
name: write-report
description: Write and render a new fungal-cv-qdrant experiment report, including diagrams and PDF compilation.
---

# Write Report

Use this when you need to create or update a report under `repos/fungal-cv-qdrant/report/`.

## Responsibilities

- inspect existing report structure before creating files
- gather experiment evidence from code, logs, CSVs, and specs
- call diagram rendering when diagrams are needed
- compile the final report and return the PDF path

## Output

Return rendered asset relative paths for direct inclusion in LaTeX.
