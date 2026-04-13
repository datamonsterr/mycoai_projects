# Rule: Backend Reimplementation Boundary

When implementing new product behavior in `mycoai_retrieval_backend/` that is
informed by `fungal-cv-qdrant/` experiments:

- Inspect experiment code, reports, and artifacts to understand the validated
  behavior.
- Reimplement the required behavior inside `mycoai_retrieval_backend/`.
- Do NOT import Python modules, helpers, or runtime code directly from
  `fungal-cv-qdrant/`.
- Prefer validated artifacts, documented schemas, and explicit payloads as the
  integration boundary between repos.
- Name the experiment source paths, producer command, and consumed artifact in
  the spec, plan, tasks, and PR summary.
- Add backend-local tests that pin the translated behavior. Tests must not rely
  on importing experiment code either.

If the product requirement cannot be satisfied without a new shared contract,
document that contract explicitly instead of creating an implicit code-level
dependency.
