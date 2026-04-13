# Rule: TypeScript Conventions

Use these conventions for `mycoai_retrieval_frontend/` and other TypeScript
work in this monorepo:

- Prefer `type` aliases for object and union shapes unless interface merging is
  specifically needed.
- Use `import type` for type-only imports.
- Avoid `any`, `enum`, and non-null assertions unless a local comment explains
  why they are unavoidable.
- Prefer literal unions, discriminated unions, and exhaustive branching over
  stringly typed conditionals.
- Keep components and helpers small and explicit. Pull logic into plain typed
  helpers before introducing custom hooks.
- Prefer immutable array helpers such as `toSorted()` and `map()` over mutating
  array operations on props or state.
- Use the existing `@/*` alias for frontend-local imports.
- Compose class names through existing utilities such as `cn` or `clsx` rather
  than manual string concatenation.
- Follow the existing ESLint and TypeScript configuration instead of adding a
  parallel style system.
- For React 19 code, prefer `startTransition`, `useDeferredValue`, and
  `useEffectEvent` when they make a concrete difference. Do not add
  `useMemo` or `useCallback` by default.

Verification for TypeScript changes must include:

- `pnpm --dir mycoai_retrieval_frontend lint`
- `pnpm --dir mycoai_retrieval_frontend typecheck`
- `pnpm --dir mycoai_retrieval_frontend build`
