from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from mycoai_retrieval_backend.app import create_app
from mycoai_retrieval_backend.core.security import hash_password
from mycoai_retrieval_backend.database import Base, get_db
from mycoai_retrieval_backend.models import User

TEST_DB_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture(scope="function")
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(
    engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession]:
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_session_factory(engine: AsyncEngine):
    """Session factory for overriding app's get_db dependency."""
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with async_session() as session:
            yield session
            await session.commit()

    return override_get_db


@pytest_asyncio.fixture(scope="function", autouse=True)
async def seed_users(engine: AsyncEngine):
    """Seed required test users so login-dependent tests can pass."""
    async_session = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        session.add_all(
            [
                User(
                    email="owner@mycoai.dev",
                    password_hash=hash_password("password123"),
                    name="Owner",
                    role="owner",
                ),
                User(
                    email="user@mycoai.dev",
                    password_hash=hash_password("password123"),
                    name="User",
                    role="user",
                ),
            ]
        )
        await session.commit()


@pytest.fixture(scope="function")
def client(test_session_factory):
    app = create_app()
    app.dependency_overrides[get_db] = test_session_factory
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
