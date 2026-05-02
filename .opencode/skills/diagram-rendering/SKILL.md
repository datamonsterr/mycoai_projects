---
name: diagram-rendering
description: Create a diagram with Mermaid or Python, render it to an image inside the report output folder, and return the relative include path.
---

# Diagram Rendering

Use this when a report or spec needs a rendered diagram.

## Responsibilities

- prefer Mermaid when it fits
- use Python for charts or layouts Mermaid cannot express well
- write outputs to the requested report image folder
- return the relative path to include in the report
