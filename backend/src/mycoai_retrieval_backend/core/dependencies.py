import uuid
from typing import Annotated

import jwt
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User
from .exceptions import AuthenticationError, AuthorizationError
from .security import decode_access_token


async def get_current_user(
    authorization: Annotated[str, Header(description="Bearer <token>")] = "",
    db: Annotated[AsyncSession | None, Depends(get_db)] = None,
) -> User:
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as err:
        raise AuthenticationError("Invalid or expired token") from err
    if payload.get("type") != "access":
        raise AuthenticationError("Token is not an access token")
    user_id = uuid.UUID(payload["sub"])
    assert db is not None  # FastAPI always injects the dependency
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(required_role: str):
    async def role_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role != required_role:
            raise AuthorizationError(
                f"Role '{required_role}' required, got '{user.role}'"
            )
        return user

    return role_checker


def require_owner():
    async def owner_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role != "owner":
            raise AuthorizationError("Role 'owner' required")
        return user

    return owner_checker


CurrentOwner = Annotated[User, Depends(require_owner())]
