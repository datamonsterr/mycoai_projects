from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYCOAI_BACKEND_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "MycoAI Retrieval Backend"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://mycoai:mycoai@localhost:5432/mycoai"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    upload_root: Path = Path("Dataset/uploads")
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7


class QdrantSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYCOAI_QDRANT_",
        env_file=".env",
        extra="ignore",
    )

    host: str = "localhost"
    port: int = 6333
    grpc_port: int = 6334
    collection_name: str = "myco_fungi_features_full_finetuned"
    default_vector_name: str = "EfficientNetB1_finetuned"
    prefer_grpc: bool = False
    timeout_seconds: int = 30
    batch_timeout_seconds: int = 300
    api_key: str | None = None
    url: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_qdrant_settings() -> QdrantSettings:
    return QdrantSettings()
