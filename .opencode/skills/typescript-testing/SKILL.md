---
name: typescript-testing
description: Write focused TypeScript unit and end-to-end tests for the MycoAI frontend using repo-aligned conventions.
version: 1.0.0
author: project
---

# TypeScript Testing

## Use When

- Editing `mycoai_retrieval_frontend/`
- Fixing a frontend regression
- Adding scientist-facing UI flows that need automated coverage
- Designing or expanding the frontend test harness

## Default Strategy

1. Add the smallest useful automated test around changed behavior
2. Prefer component or helper tests for local logic
3. Prefer end-to-end tests for flows that cross routing, forms, async loading,
   or backend integration
4. Pair automated tests with a manual browser check for user-facing changes

## Project Conventions

- Treat the repo as `React 19 + Vite + TypeScript`
- Follow the local TypeScript and ESLint configuration before adding new test
  abstractions
- If unit tests are needed and no harness exists yet, add the smallest viable
  Vitest setup that serves the current feature instead of building a large test
  framework up front
- Use Playwright-style e2e coverage when the change is best verified through a
  browser journey

## What Good Frontend Tests Look Like

- Assert user-visible behavior, not implementation details
- Keep fixtures small and readable
- Prefer semantic queries and realistic interactions
- Cover loading, empty, error, and success states when they are part of the
  feature contract
- Keep generated snapshots to a minimum; prefer explicit assertions

## Verification Commands

```bash
pnpm --dir mycoai_retrieval_frontend lint
pnpm --dir mycoai_retrieval_frontend typecheck
pnpm --dir mycoai_retrieval_frontend build
```

If the repo adds unit or e2e scripts, run them as part of the feature's local
definition of done.
