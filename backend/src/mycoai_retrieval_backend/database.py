from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


def _build_url(db_url: str) -> str:
    if db_url.startswith("postgresql"):
        return db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return db_url


_engine = create_async_engine(
    _build_url(get_settings().database_url),
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session


class Base(DeclarativeBase):
    pass
