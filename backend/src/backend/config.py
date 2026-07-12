from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    default_vector_name: str = "efficientnetb1_finetuned"
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


class StorageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MYCOAI_BACKEND_STORAGE_",
        env_file=".env",
        extra="ignore",
    )

    backend: Literal["local", "s3"] = "local"
    upload_root: Path = Path("Dataset/uploads")

    s3_endpoint: str = "minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "mycoai-images"
    s3_secure: bool = False
    s3_public_endpoint: str = "http://localhost:9000"
    s3_presigned_expiry: int = 3600


@lru_cache(maxsize=1)
def get_storage_settings() -> StorageSettings:
    return StorageSettings()
