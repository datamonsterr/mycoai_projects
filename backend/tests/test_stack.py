from __future__ import annotations

from backend._qdrant_factory import create_qdrant_client
from backend.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from backend.celery_app import create_celery_app
from backend.config import Settings
from backend.db import create_engine, create_sessionmaker


def test_config_defaults() -> None:
    s = Settings()
    assert s.app_name == "MycoAI Retrieval Backend"
    assert s.host == "0.0.0.0"
    assert s.port == 8000
    assert s.database_url
    assert s.qdrant_port == 6333
    assert s.jwt_algorithm == "HS256"
    assert s.jwt_access_token_expire_minutes == 30
    assert s.celery_broker_url == "redis://localhost:6379/0"


def test_sqlalchemy_engine_creation() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    assert engine is not None
    assert engine.url.drivername == "sqlite+aiosqlite"


def test_sessionmaker_creation() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    sm = create_sessionmaker(engine)
    assert sm is not None


def test_hash_and_verify_password() -> None:
    hashed = hash_password("secret123")
    assert hashed != "secret123"
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip() -> None:
    token = create_access_token("user-1")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"


def test_refresh_token_has_type() -> None:
    token = create_refresh_token("user-1")
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["type"] == "refresh"


def test_qdrant_client_creation() -> None:
    client = create_qdrant_client()
    assert client is not None


def test_celery_app_creation() -> None:
    celery = create_celery_app()
    assert celery is not None
    assert celery.main == "mycoai_backend"
