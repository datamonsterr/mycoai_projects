"""Create a dataowner user in the MycoAI backend.

Usage:
    docker compose -f docker-compose.yml -f docker-compose.dev.yml \
        exec backend uv run python scripts/create_dataowner.py admin@example.com
"""

import argparse
import secrets
import asyncio

from mycoai_retrieval_backend.database import _get_engine, _get_sessionmaker
from mycoai_retrieval_backend.models import User
from mycoai_retrieval_backend.core.security import hash_password
from sqlalchemy import select


def create_dataowner(email: str) -> None:
    engine = _get_engine()
    sessionmaker = _get_sessionmaker()

    async def _run():
        async with sessionmaker() as session:
            existing = await session.scalar(
                select(User).where(User.email == email)
            )
            if existing is not None:
                print(f"[SKIP] {email} exists (role={existing.role})")
                return

            user = User(
                email=email,
                name=email.split("@")[0],
                password_hash=hash_password(secrets.token_urlsafe(16)),
                role="dataowner",
            )
            session.add(user)
            await session.commit()
            print(f"[OK] dataowner created: {email}")

    asyncio.run(_run())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a dataowner user")
    parser.add_argument("email", help="User email")
    args = parser.parse_args()
    create_dataowner(args.email)
