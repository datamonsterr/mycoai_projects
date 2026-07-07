---
inclusion: fileMatch
fileMatchPattern: "**/backend/**"
---

# Backend Reimplementation Boundary

When implementing product behavior in `backend/` informed by `research/` experiments:

- Inspect experiment code, reports, and artifacts to understand validated behavior
- Reimplement required behavior inside `backend/`
- Do NOT import Python modules or runtime code from `research/`
- Use validated artifacts, documented schemas, and explicit payloads as the integration boundary
- Name experiment source paths, producer command, and consumed artifact in spec/plan/PR summary
- Add backend-local tests that pin the translated behavior (tests must not import experiment code)

If a requirement needs a shared contract, document it explicitly instead of creating implicit code-level dependencies.
