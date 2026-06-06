---
name: mistake
description: Record a mistake, its context, and fix rule into rules/*.md so future report runs avoid repeating it.
category: rules
---

# /mistake

Usage:

```
/mistake <area> <mistake> -> <fix>
```

When user reports a mistake:
1. Classify area: `srs`, `db_schema`, `report`, `diagram`, `chart`, `workflow`, or `general`.
2. Update `rules/<area>.md` directly.
3. Add entry:
   - Context
   - Mistake
   - Correct rule
   - Example fix
4. Keep rule general, reusable, short.
5. Confirm changed file path.
