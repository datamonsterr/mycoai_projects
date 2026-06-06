from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


def _build_url(db_url: str) -> str:
    if db_url.startswith("postgresql"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db_url


_engine = None
_async_session_local = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            _build_url(get_settings().database_url),
            echo=False,
        )
    return _engine


def _get_sessionmaker():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_local


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with _get_sessionmaker()() as session:
        yield session


class Base(DeclarativeBase):
    pass
