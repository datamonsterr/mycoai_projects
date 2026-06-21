from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Protocol

from ..config import StorageSettings


class ObjectStorage(Protocol):
    """Protocol for object storage backends (local filesystem or S3/MinIO)."""

    def upload_bytes(
        self, key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        ...

    def get_url(self, key: str) -> str:
        ...

    def get_bytes(self, key: str) -> bytes | None:
        ...

    def delete(self, key: str) -> None:
        ...

    def object_exists(self, key: str) -> bool:
        ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def upload_bytes(
        self, key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"/static/{key}"

    def get_url(self, key: str) -> str:
        return f"/static/{key}"

    def get_bytes(self, key: str) -> bytes | None:
        path = self.root / key
        if path.exists():
            return path.read_bytes()
        return None

    def delete(self, key: str) -> None:
        path = self.root / key
        path.unlink(missing_ok=True)

    def object_exists(self, key: str) -> bool:
        return (self.root / key).exists()


class S3Storage:
    def __init__(self, settings: StorageSettings) -> None:
        from minio import Minio  # type: ignore[import-untyped]

        self._client = Minio(
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            secure=settings.s3_secure,
        )
        self._bucket = settings.s3_bucket
        self._presigned_expiry = settings.s3_presigned_expiry

    def ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload_bytes(
        self, key: str, data: bytes, content_type: str = "image/jpeg"
    ) -> str:
        import io

        self._client.put_object(
            bucket_name=self._bucket,
            object_name=key,
            data=io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return f"s3://{self._bucket}/{key}"

    def get_url(self, key: str) -> str:
        return self._client.presigned_get_object(
            bucket_name=self._bucket,
            object_name=key,
            expires=timedelta(seconds=self._presigned_expiry),
        )

    def get_bytes(self, key: str) -> bytes | None:
        try:
            response = self._client.get_object(self._bucket, key)
            return response.read()
        except Exception:
            return None
        finally:
            if "response" in locals():
                response.close()
                response.release_conn()

    def delete(self, key: str) -> None:
        self._client.remove_object(self._bucket, key)

    def object_exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except Exception:
            return False


def create_storage(settings: StorageSettings) -> ObjectStorage:
    if settings.backend == "s3":
        storage = S3Storage(settings)
        storage.ensure_bucket()
        return storage
    return LocalStorage(settings.upload_root)
