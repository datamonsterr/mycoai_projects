from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User


class UserRepository:
    @staticmethod
    async def get_user(db: AsyncSession, user_id: str) -> User | None:
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(user_id))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_users(
        db: AsyncSession,
        role: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[User]:
        stmt = select(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        stmt = stmt.offset(offset).limit(limit).order_by(User.created_at.desc())
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def count_users(
        db: AsyncSession,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(User)
        if role is not None:
            stmt = stmt.where(User.role == role)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        result = await db.execute(stmt)
        return result.scalar_one()

    @staticmethod
    async def count_active_owners(db: AsyncSession) -> int:
        result = await db.execute(
            select(func.count())
            .select_from(User)
            .where(User.role == "owner", User.is_active.is_(True))
        )
        return result.scalar_one()

    @staticmethod
    async def update_user_role(
        db: AsyncSession, user_id: str, role: str
    ) -> User | None:
        user = await UserRepository.get_user(db, user_id)
        if user is not None:
            user.role = role
            await db.flush()
        return user

    @staticmethod
    async def update_user_status(
        db: AsyncSession, user_id: str, is_active: bool
    ) -> User | None:
        user = await UserRepository.get_user(db, user_id)
        if user is not None:
            user.is_active = is_active
            await db.flush()
        return user
