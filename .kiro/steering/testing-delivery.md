# Testing and Delivery Strategy

## Change Classification

Classify every change first: experiment, backend, frontend, or shared-contract.

## Validation by Context

| Context | Commands |
|---------|----------|
| Experiments | `uv --directory fungal-cv-qdrant ...`, validate logs/artifacts |
| Backend | `uv --directory backend run ruff check`, `ruff format --check`, `mypy`, `pytest` |
| Frontend | `pnpm --dir mycoai_retrieval_frontend lint`, `typecheck`, `build` |
| Shared contracts | Validate both producer and consumer repos |

## Definition of Done

- Implementation is complete
- Local checks pass
- CI workflow checks pass (or blocker is recorded)
- Manual validation recorded for user-facing changes
- PR-ready summary includes: spec, plan, tasks, validation, contract impact, residual risks
