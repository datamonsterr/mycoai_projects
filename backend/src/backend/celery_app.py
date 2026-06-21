from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]

from .config import get_settings


def create_celery_app() -> Celery:
    settings = get_settings()
    return Celery(
        "mycoai_backend",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )
