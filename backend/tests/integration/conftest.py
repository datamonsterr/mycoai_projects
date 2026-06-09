from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from mycoai_retrieval_backend.database import Base

POSTGRES_URL = os.getenv(
    "MYCOAI_TEST_DB_URL",
    "postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai_test",
)
REDIS_URL = os.getenv("MYCOAI_TEST_REDIS_URL", "redis://localhost:6379/1")
QDRANT_HOST = os.getenv("MYCOAI_TEST_QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("MYCOAI_TEST_QDRANT_PORT", "6333"))


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


# ── Postgres ──────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def pg_engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(POSTGRES_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(
    pg_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(
        bind=pg_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ── Redis ─────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def redis_client():
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(REDIS_URL, decode_responses=True)
        await client.ping()
    except Exception:
        pytest.skip("Redis not available")

    yield client

    keys = await client.keys("test:*")
    if keys:
        await client.delete(*keys)
    await client.aclose()


# ── Qdrant ────────────────────────────────────────────────────────────


@pytest_asyncio.fixture(scope="function")
async def qdrant_client():
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        client.health_check()
    except Exception:
        pytest.skip("Qdrant not available")

    yield client

    client.close()


# ── Test user helpers used by multiple integration test modules ──────


TEST_USER_EMAIL = "integration@test.local"
TEST_USER_PASSWORD = "integration-password-123"
TEST_USER_NAME = "Integration User"
TEST_USER_ROLE = "owner"


@pytest_asyncio.fixture(scope="function")
async def test_user_id(pg_session: AsyncSession) -> uuid.UUID:
    from mycoai_retrieval_backend.models import User

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=TEST_USER_EMAIL,
        password_hash="hashed",
        name=TEST_USER_NAME,
        role=TEST_USER_ROLE,
        is_active=True,
    )
    pg_session.add(user)
    await pg_session.flush()
    return user_id
