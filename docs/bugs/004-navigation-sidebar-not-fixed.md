# Bug 004: Navigation sidebar scrolls with content

**Status:** CONFIRMED | **Severity:** Medium | **Component:** Frontend

## Root Cause

`frontend/src/components/layout.tsx:74` — `lg:relative` overrides `fixed` at ≥1024px, making sidebar part of normal document flow. Main content area lacks `h-screen overflow-y-auto`.

```tsx
// line 71-76 — contradictory positioning
<aside className={cn(
  'fixed inset-y-0 left-0 ...',  // fixed ✅
  'lg:relative ...',               // overrides to relative ❌
)}>
```

```tsx
// line 169 — missing scroll containment
<div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
```

## Solution

1. Remove `lg:relative` from sidebar (line 74)
2. Add `h-screen overflow-y-auto` to main content area (line 169)
3. Add left margin to account for fixed sidebar width

```diff
- 'lg:relative lg:translate-x-0',
+ 'lg:translate-x-0',
```

```diff
- <div className="flex-1 flex flex-col min-w-0 overflow-x-hidden">
+ <div className="flex-1 flex flex-col h-screen overflow-y-auto min-w-0">
```

## Files to Modify

- `frontend/src/components/layout.tsx` (lines 74, 169)
