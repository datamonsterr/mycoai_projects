---
name: pytest-unit-testing
description: Write focused pytest unit and API tests for Python code in the MycoAI monorepo, especially `repos/mycoai_retrieval_backend/`.
version: 1.0.0
author: project
---

# Pytest Unit Testing

## Use When

- Editing `repos/mycoai_retrieval_backend/` behavior
- Fixing a Python bug and needing regression coverage
- Translating experiment behavior into backend product code
- Adding API contract or service tests

## Goals

- Prefer the smallest useful test that proves behavior
- Keep tests inside the owning repo
- Avoid importing runtime code from `fungal-cv-qdrant/` into backend tests

## Default Test Order

1. Pure function or serializer unit test
2. Service-level test
3. FastAPI route test with `TestClient`
4. Integration-style test only when lower layers are insufficient

## Project Conventions

- Use `uv --directory repos/mycoai_retrieval_backend run pytest`
- Keep tests under `repos/mycoai_retrieval_backend/tests/`
- Prefer local fixtures unless reused across multiple files
- Mock network, filesystem, or external service boundaries
- Assert stable response shapes for API contracts
- Use `pytest.mark.parametrize` for algorithm or edge-case matrices

## When Reimplementing Experiment Logic

- Read the relevant `fungal-cv-qdrant/src/experiments/...` files as reference
- Translate the logic into backend-owned code
- Create backend-local fixtures that capture representative validated inputs and
  outputs
- Test the translated behavior directly without importing experiment modules

## Verification Commands

```bash
uv --directory repos/mycoai_retrieval_backend run ruff check .
uv --directory repos/mycoai_retrieval_backend run ruff format --check .
uv --directory repos/mycoai_retrieval_backend run mypy src
uv --directory repos/mycoai_retrieval_backend run pytest
```
