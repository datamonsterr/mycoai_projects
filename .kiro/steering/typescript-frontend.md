---
inclusion: fileMatch
fileMatchPattern: "**/mycoai_retrieval_frontend/**"
---

# TypeScript & React Frontend Conventions

## TypeScript Rules

- Prefer `type` aliases over `interface` unless merging is needed
- Use `import type` for type-only imports
- Avoid `any`, `enum`, and non-null assertions unless locally justified
- Prefer literal unions and discriminated unions over stringly typed conditionals
- Keep components small; pull logic into plain typed helpers before custom hooks
- Prefer immutable array helpers (`toSorted()`, `map()`) over mutations
- Use the existing `@/*` alias for frontend-local imports
- Compose class names through `cn` or `clsx`
- Follow existing ESLint and TypeScript configuration

## React 19 (Vite, NOT Next.js)

- This is React 19 + Vite, not Next.js — do not use Next.js APIs
- Prefer `startTransition`, `useDeferredValue`, `useEffectEvent` when they improve UX
- Do NOT add `useMemo` or `useCallback` by default
- Add transitions only when they clarify navigation or feedback
- Preserve the scientist-facing design language unless explicitly redesigning
- Avoid barrel imports, reduce re-renders, split expensive renders

## Verification

Always run after TypeScript/frontend changes:

```bash
pnpm --dir mycoai_retrieval_frontend lint
pnpm --dir mycoai_retrieval_frontend typecheck
pnpm --dir mycoai_retrieval_frontend build
```
