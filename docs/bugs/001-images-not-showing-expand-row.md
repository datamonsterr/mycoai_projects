# Bug 001: Images not showing when expand row in Dataset Browser

**Status:** CONFIRMED | **Severity:** High | **Component:** Frontend

## Root Cause

`frontend/src/pages/Dataset.tsx:257,286,289` + `backend/.../routes.py:134`

The API always populates `source_url` as `/api/v1/images/{id}/source` (auth-protected endpoint) for every image. In `Dataset.tsx`, `<img>` tags use:
```tsx
src={img.source_url || resolveImageUrl(img.file_path)}
```

Since `source_url` is always a non-empty string, the `resolveImageUrl` fallback NEVER fires. Browser `<img>` tags issue bare GET requests without auth headers → 401/403 → no image renders.

The `/static/` mount (via `resolveImageUrl`) serves files without auth — this is what browser `<img>` tags need.

## Solution

Change all `<img src>` in `Dataset.tsx` to use `resolveImageUrl(img.file_path)` directly:

| Line | Current | Fix |
|------|---------|-----|
| 257 | `img.source_url \|\| resolveImageUrl(img.file_path)` | `resolveImageUrl(img.file_path)` |
| 286 | `img.source_url \|\| resolveImageUrl(img.file_path)` | `resolveImageUrl(img.file_path)` |
| 289 | `img.source_url \|\| resolveImageUrl(img.file_path)` | `resolveImageUrl(img.file_path)` |

## Files to Modify

- `frontend/src/pages/Dataset.tsx` (lines 257, 286, 289)
