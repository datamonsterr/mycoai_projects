"""
Provision initial Data Owner by email.

Usage:
    python -m mycoai_retrieval_backend.create_owner \
        --email owner@example.com [--password ...]
"""

import argparse
import asyncio
import secrets
import string

from .core.security import hash_password
from .database import _get_sessionmaker
from .models import User


def _generate_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def _create_owner(email: str, password: str | None) -> None:
    if password is None:
        password = _generate_password()

    password_hash = hash_password(password)

    async with _get_sessionmaker()() as db:
        user = User(
            email=email,
            password_hash=password_hash,
            name=email.split("@")[0],
            role="owner",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Owner created: {user.id}")
        print(f"  email:     {user.email}")
        print(f"  name:      {user.name}")
        print(f"  role:      {user.role}")
        print(f"  password:  {password}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Provision initial Data Owner",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Owner email address",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Owner password (random 16-char if omitted)",
    )
    args = parser.parse_args()
    asyncio.run(_create_owner(args.email, args.password))


if __name__ == "__main__":
    main()
