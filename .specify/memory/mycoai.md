# MycoAI Speckit Memory

- Monorepo root coordinates three repos: `repos/fungal-cv-qdrant/`, `repos/mycoai_retrieval_backend/`, `repos/mycoai_retrieval_frontend/`.
- Default `src/`, `docs/`, `report/` paths mean `repos/fungal-cv-qdrant/` unless backend/frontend named.
- Use `uv`/`uvx` for Python, `pnpm` for frontend, `gh` for GitHub.
- Keep product repos independent: backend/frontend may inspect experiments but must not import from `repos/fungal-cv-qdrant/`.
- Verification: backend `ruff check`, `ruff format --check`, `mypy`, `pytest`; frontend `pnpm lint`, `typecheck`, `build`; experiments relevant `uv --directory fungal-cv-qdrant ...`.
- Keep context lean: load only owning repo files, prefer Task/explore for broad search, avoid shared data dirs unless requested.
