from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.dependencies import CurrentUser
from ..core.exceptions import AuthenticationError, ConflictError
from ..core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from ..database import get_db
from ..models import InviteToken, RefreshToken, User
from ..schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterWithTokenRequest,
    TokenResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise ConflictError("User with this email already exists")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        role="user",
    )
    db.add(user)
    await db.flush()

    user_id_str = str(user.id)
    settings = get_settings()
    access_token = create_access_token(user_id_str, user.role)
    refresh_token = create_refresh_token(user_id_str)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.refresh_token_expire_seconds),
    )
    db.add(rt)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post("/register-with-token", response_model=TokenResponse, status_code=201)
async def register_with_token(
    data: RegisterWithTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    token_hash_val = hash_token(data.token)
    invite = await db.scalar(
        select(InviteToken)
        .where(InviteToken.token_hash == token_hash_val)
        .where(InviteToken.email == data.email)
        .where(InviteToken.is_used.is_(False))
    )
    if invite is None:
        raise AuthenticationError("Invalid or expired invite token")

    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        if existing.is_active:
            raise ConflictError("User with this email already exists")
        existing.password_hash = hash_password(data.password)
        existing.name = data.name
        existing.is_active = True
        user = existing
    else:
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            name=data.name,
            role="user",
            is_active=True,
        )
        db.add(user)
    await db.flush()

    invite.is_used = True
    await db.flush()

    user_id_str = str(user.id)
    settings = get_settings()
    access_token = create_access_token(user_id_str, user.role)
    refresh_token = create_refresh_token(user_id_str)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.refresh_token_expire_seconds),
    )
    db.add(rt)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    user = await db.scalar(select(User).where(User.email == data.email))
    if user is None or not verify_password(data.password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    if not user.is_active:
        raise AuthenticationError("Account is inactive")

    user_id_str = str(user.id)
    settings = get_settings()
    access_token = create_access_token(user_id_str, user.role)
    refresh_token = create_refresh_token(user_id_str)

    rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC)
        + timedelta(seconds=settings.refresh_token_expire_seconds),
    )
    db.add(rt)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    settings = get_settings()
    token_hash = hash_token(data.refresh_token)

    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if rt is None:
        raise AuthenticationError("Invalid refresh token")

    rt_expires = rt.expires_at
    if rt_expires.tzinfo is None:
        rt_expires = rt_expires.replace(tzinfo=UTC)
    if rt_expires < datetime.now(UTC):
        raise AuthenticationError("Refresh token expired")

    try:
        payload: dict[str, object] = jwt.decode(
            data.refresh_token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as err:
        raise AuthenticationError("Invalid refresh token") from err

    if payload.get("type") != "refresh":
        raise AuthenticationError("Token is not a refresh token")

    user_id_str = str(payload["sub"])
    user = await db.scalar(select(User).where(User.id == UUID(user_id_str)))
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")

    access_token = create_access_token(user_id_str, user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=data.refresh_token,
        expires_in=settings.access_token_expire_seconds,
    )


@router.post("/logout", status_code=204)
async def logout(
    data: RefreshRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    token_hash = hash_token(data.refresh_token)
    rt = await db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    if rt is not None:
        await db.delete(rt)
        await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
    )
