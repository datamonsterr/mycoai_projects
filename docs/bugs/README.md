# Bug Reports Index

All 9 bugs CONFIRMED. Root causes identified with specific files and line numbers.

| # | Bug | Severity | Root Cause File:Line |
|---|-----|----------|---------------------|
| 001 | Images not showing in expand row | High | `Dataset.tsx:257,286,289` — source_url always set, bypasses resolveImageUrl |
| 002 | No download template button | Medium | Feature not implemented — no template CSV, no backend endpoint |
| 003 | Remove test metadata/strain | Low | No bulk-delete endpoint for test data cleanup |
| 004 | Navigation sidebar not fixed | Medium | `layout.tsx:74` — `lg:relative` overrides `fixed` |
| 005 | 403 Forbidden data-owner /admin/users | High | `dependencies.py:57` — require_owner() rejects "dataowner" |
| 006 | Model/index info hidden, no reindex button | High | Same as 005 + frontend isOwner checks exclude dataowner |
| 007 | Retrieval pipeline not implemented | High | `api/retrieval.py` returns hardcoded fake data |
| 008 | Email invite not working | High | No backend endpoint, no email infra, frontend button is no-op |
| 009 | Dashboard missing charts, card alignment | Medium | 4 issues: missing charts, wrong row, missing auto-rows-fr, no h-full |

## Cross-Cutting Patterns

1. **dataowner ≠ owner gap:** Bugs 005 and 006 share the same root cause — the backend `require_owner()` dependency and 3 frontend files hardcode `=== 'owner'`, excluding `'dataowner'` role.
2. **Auth-protected URLs in `<img>` tags:** Bug 001 — `source_url` points to authenticated endpoints that browser `<img>` tags can't access.
3. **Stub implementations:** Bugs 007 and 008 — backend API endpoints return hardcoded/fake data or are complete no-ops.
4. **CSS layout regression:** Bug 004 — `lg:relative` on sidebar conflicts with `fixed` positioning. Bug 009 — grid lacks height-enforcing classes.

## Recommended Fix Order

1. **Bugs 005+006** (dataowner role) — one backend change fixes both, unblocks other features
2. **Bug 001** (images) — 3-line fix, high user impact
3. **Bug 004** (sidebar) — 3-line CSS fix
4. **Bug 008** (email invite) — needs infrastructure + backend endpoint
5. **Bug 007** (retrieval pipeline) — largest effort, full pipeline reimplementation
6. **Bug 009** (dashboard) — moderate effort, backend + frontend
7. **Bug 002** (template download) — quick frontend addition
8. **Bug 003** (test cleanup) — low priority, optional
