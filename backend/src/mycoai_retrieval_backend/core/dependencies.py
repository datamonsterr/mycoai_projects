from typing import Annotated

import jwt
from fastapi import Depends, Header

from ..services.stores import get_user_store
from .exceptions import AuthenticationError, AuthorizationError
from .security import decode_access_token


async def get_current_user(
    authorization: Annotated[str, Header(description="Bearer <token>")] = "",
) -> dict:
    if not authorization.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid Authorization header")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as err:
        raise AuthenticationError("Invalid or expired token") from err
    if payload.get("type") != "access":
        raise AuthenticationError("Token is not an access token")
    user_id = payload["sub"]
    store = get_user_store()
    user = store.get(user_id)
    if not user or not user.get("is_active", True):
        raise AuthenticationError("User not found or inactive")
    return user


def require_role(required_role: str):
    async def role_checker(
        user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        if user.get("role") != required_role:
            raise AuthorizationError(
                f"Role '{required_role}' required, got '{user.get('role')}'"
            )
        return user

    return role_checker
