# Testing Strategy

## Overview

MycoAI Retrieval Backend uses a layered testing approach: fast SQLite-based unit tests for the inner loop, Docker-backed integration tests for external services, and manual validation for full user journeys.

## Principles

- **Tests verify behavior through public interfaces, not implementation details.** Tests survive refactors because they assert what the system does, not how.
- **Fast feedback.** Unit tests run in under 5 minutes. Integration tests are optional and opt-in for CI.
- **One test, one behavior.** Each test proves exactly one thing. Test names describe the capability they verify.
- **Tests are documentation.** Reading a test file should explain how to use the corresponding module.

## Test Taxonomy

```
tests/
├── conftest.py                     # Unit test fixtures (SQLite)
├── conftest_integration.py         # Integration test fixtures (Postgres/Redis/Qdrant)
├── test_models*.py                 # ORM model constraints
├── test_schemas*.py                # Pydantic validation
├── test_repos*.py                  # Repository (data access) layer
├── test_core.py                    # Business logic (security, auth)
├── test_rbac.py                    # Role-based access control
├── test_audit.py                   # Audit logging
├── test_error_format.py            # Error response contracts (RFC 7807)
├── test_auth_flow.py               # Authentication lifecycle
├── test_qdrant.py                  # Qdrant filters, aggregation, ops (mocked)
├── test_integration_postgres.py    # PostgreSQL connection (Docker required)
├── test_integration_redis.py       # Redis connection (Docker required)
├── test_integration_qdrant.py      # Qdrant connection (Docker required)
├── test_integration_api.py         # Full API journey (Docker required)
└── routes/
    ├── conftest.py                 # Route test client (dependency override)
    ├── test_auth.py                # /api/v1/auth/*
    ├── test_species.py             # /api/v1/species/*
    ├── test_feedback.py            # /api/v1/feedback/*
    ├── test_admin.py               # /api/v1/admin/*
    ├── test_dashboard.py           # /api/v1/dashboard/*
    └── test_retrieval.py           # /api/v1/retrieval/*
```

## Layer Map

| Layer | Fixture | DB | When to Test |
|-------|---------|-----|--------------|
| **Schema** (Pydantic) | None | — | Always — validates request/response shapes |
| **Model** (SQLAlchemy) | `session` | SQLite | Always — constraint enforcement, relationships |
| **Repo** (data access) | `session` | SQLite | Always — query logic, pagination, uniqueness |
| **Service** (business logic) | `session` or mock | SQLite | When logic spans multiple models/repos |
| **Route** (API endpoint) | `client` (overrides `get_db`) | SQLite | Always — contract, auth, error handling |
| **Integration** | `pg_session`, `redis_client`, `qdrant_client` | Real services | Before merge — service connectivity, real SQL |

## Unit Tests (SQLite)

### Philosophy

Unit tests run against an in-memory SQLite database. Each test function gets a clean database via `conftest.py`. Tests never hit the network or filesystem.

### Write Unit Tests When

- Adding a new Pydantic schema with validation rules
- Adding a new SQLAlchemy model or constraint
- Adding a new repository query
- Changing an API endpoint's request/response contract
- Changing authentication or authorization logic
- Changing error response format

### Patterns

#### Model test

```python
async def test_species_name_must_be_unique(session: AsyncSession):
    session.add(Species(name="Penicillium", description="Mold"))
    await session.flush()
    session.add(Species(name="Penicillium", description="Duplicate"))
    with pytest.raises(IntegrityError):
        await session.commit()
```

#### Schema test

```python
def test_invalid_email_rejected():
    with pytest.raises(ValidationError):
        RegisterRequest(email="not-an-email", password="password123", name="Test")
```

#### Route test

```python
def test_list_species_returns_paginated(client, owner_headers):
    resp = client.get("/api/v1/species", headers=owner_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data and "total" in data
```

#### RBAC test

```python
def test_create_species_forbidden_for_user(client, user_headers):
    resp = client.post("/api/v1/species", json={"name": "Foo"}, headers=user_headers)
    assert resp.status_code == 403
```

### How the SQLite Override Works

`conftest.py` creates a fresh SQLite engine per test function. The `client` fixture calls `create_app()` and overrides `get_db`:

```python
@pytest.fixture(scope="function")
def client(test_session_factory):
    app = create_app()
    app.dependency_overrides[get_db] = test_session_factory
    with TestClient(app) as client:
        yield client
```

Set the env variable before running to prevent the app-level engine from trying Postgres:

```bash
DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest -m "not integration"
```

## Integration Tests (Real Services)

### Philosophy

Integration tests verify connectivity and behavior against real PostgreSQL, Redis, and Qdrant instances. They auto-skip when services are unavailable, making them safe for local development and CI.

### Docker Compose Setup

```bash
# Start required services
docker compose -f docker-compose.dev.yml up -d postgres redis qdrant

# Run integration tests
uv --directory backend run pytest tests/ -m integration

# Stop services
docker compose -f docker-compose.dev.yml down
```

### Services Under Test

| Service | Test File | Markers | What It Covers |
|---------|-----------|---------|----------------|
| PostgreSQL | `test_integration_postgres.py` | `integration_postgres` | ORM queries, transactions, FK constraints, concurrent access |
| Redis | `test_integration_redis.py` | `integration_redis` | SET/GET, TTL, delete, pub/sub, cache patterns |
| Qdrant | `test_integration_qdrant.py` | `integration_qdrant` | Health check, collection info, upsert/search/delete, filters |
| Full API | `test_integration_api.py` | `integration_postgres` | Register → login → refresh → logout flow, CRUD cycles, RBAC enforcement |

### Connection Defaults

Integration tests use environment variables with sensible Docker Compose defaults:

```bash
MYCOAI_TEST_DB_URL="postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai_test"
MYCOAI_TEST_REDIS_URL="redis://localhost:6379/1"
MYCOAI_TEST_QDRANT_HOST="localhost"
MYCOAI_TEST_QDRANT_PORT="6333"
```

### Graceful Skip

Every integration test follows this pattern:

```python
@pytest.mark.integration
@pytest.mark.integration_redis
async def test_redis_ping(redis_client):
    try:
        result = await redis_client.ping()
        assert result is True
    except Exception:
        pytest.skip("Redis not available")
```

### When to Write Integration Tests

- Adding a new database table — verify real PostgreSQL constraint enforcement
- Adding Redis caching — verify SET/GET with TTL
- Adding Qdrant indexing — verify upsert + search roundtrip
- Full API flow — verify complete user journey against real services

## Coverage

### Target

Aim for 85%+ coverage on production code paths. 100% on schemas and core logic. Stubs (tasks, services awaiting implementation) are excluded.

### Commands

```bash
# Coverage report
DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest \
    -m "not integration" \
    --cov=mycoai_retrieval_backend \
    --cov-report=term-missing

# Annotated source (shows ! for uncovered lines)
pytest --cov=mycoai_retrieval_backend --cov-report=annotate:cov_annotate
```

### Interpreting Coverage

- **Schema modules** (schemas/): Must be 100%. If a branch is uncovered, the schema's `@validator` or discriminated union isn't tested.
- **Core** (security, dependencies): Must be 100%. Critical auth paths.
- **Repos** (repos/): 85%+. Edge cases (nonexistent IDs, conflict errors) must be covered.
- **API routes** (api/): 80%+. Auth flows (401/403) and error responses must be covered.
- **Services** (services/): Variable. Stubs are expected to have low coverage until implementation matures.

## CI Integration

### GitHub Actions Workflow

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: astral-sh/setup-uv@v5
    - run: uv --directory backend sync --all-groups

    # Fast unit tests (SQLite, no Docker)
    - run: |
        DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest \
          -m "not integration" \
          --cov=mycoai_retrieval_backend \
          --cov-report=xml

    # Integration tests (needs services)
    - run: docker compose -f docker-compose.dev.yml up -d postgres redis qdrant
    - run: uv --directory backend run pytest -m integration
    - run: docker compose -f docker-compose.dev.yml down
```

### Pre-commit / Pre-push

```bash
# Run locally before committing
uv --directory backend run ruff check src/ tests/
uv --directory backend run mypy src
DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest -m "not integration"
```

## Debugging Test Failures

### Common Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `no such table: users` | App engine tried Postgres, test fixture not injected | Check `client` fixture uses `test_session_factory` |
| `assert 422 == 201` | Pydantic validation rejected request | Log response body: `print(resp.json())` |
| `assert 404 == 200` | Route path mismatch | Check `api/router.py` for actual prefix |
| `IntegrityError not raised` | SQLite doesn't enforce FKs by default | Skip test: `@pytest.mark.skip(reason="SQLite FK limitation")` |
| `OSError: connect call failed` | App tried real Postgres at import time | Set `DATABASE_URL="sqlite+aiosqlite://"` env var |
| `PermissionError: Missing required role` | Test user has wrong role string | Use `role="owner"` or `role="user"` |

### Quick Debug

```bash
# Run single test with full traceback
DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest tests/routes/test_auth.py::test_login -q --tb=long

# Show stdout/print during test
DATABASE_URL="sqlite+aiosqlite://" uv --directory backend run pytest tests/routes/test_auth.py -q -s

# Run specific marker
uv --directory backend run pytest -m integration_redis -q
```

## Testing Workflow (TDD)

1. **Read** the SRS use case and feature spec for the behavior
2. **Write the test first** — describe what the system should do
3. **Run** — confirm it fails (RED)
4. **Implement** the minimal code to pass (GREEN)
5. **Refactor** — extract duplication, deepen modules, re-run tests
6. **Check coverage** — ensure new code paths are covered

### What to Test First

- **Critical path**: Auth, species/feedback CRUD, retrieval
- **Error paths**: Invalid input, not found, unauthorized, forbidden
- **Edge cases**: Empty results, duplicate resources, boundary values

### What Not to Test

- Private helper functions (test through public interface)
- Framework internals (FastAPI middleware, SQLAlchemy session lifecycle)
- External service internals (mock them, don't test them)
- Trivial getters/setters (coverage will cover them through real usage)
