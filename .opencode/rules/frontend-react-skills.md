# Rule: Frontend React Skills

When touching `mycoai_retrieval_frontend/`, apply the installed Vercel React
skills as project guidance:

- Use `vercel-react-best-practices` for React performance, rendering, and data
  flow decisions.
- Use `vercel-react-view-transitions` only when motion or page transitions are
  part of the requested user experience.

Adapt those skills to this repo's actual stack:

- This frontend is `React 19 + Vite`, not Next.js. Do not introduce Next.js-only
  APIs or conventions.
- Prefer guidance that translates directly to Vite and client-rendered React:
  avoiding barrel imports, reducing re-renders, splitting expensive renders,
  and using `startTransition`, `useDeferredValue`, or `useEffectEvent` when
  they materially improve the UI.
- Preserve the existing scientist-facing design language unless the task is
  explicitly a redesign.
- Add transitions only when they clarify navigation or feedback; do not add
  decorative motion that slows down dense research workflows.
