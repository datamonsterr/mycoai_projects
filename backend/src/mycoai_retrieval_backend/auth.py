from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast

from jose import jwt  # type: ignore[import-untyped]
from passlib.context import CryptContext  # type: ignore[import-untyped]

from .config import get_settings

_pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return cast(str, _pwd_context.hash(password))


def verify_password(plain: str, hashed: str) -> bool:
    return cast(bool, _pwd_context.verify(plain, hashed))


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    settings = get_settings()
    if expires_minutes is None:
        expires_minutes = settings.jwt_access_token_expire_minutes
    expire = datetime.now(tz=UTC) + timedelta(minutes=expires_minutes)
    payload = {"sub": subject, "exp": expire}
    return cast(
        str,
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm),
    )


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(tz=UTC) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return cast(
        str,
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm),
    )


def decode_token(token: str) -> dict[str, object]:
    settings = get_settings()
    return cast(
        dict[str, object],
        jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]),
    )
