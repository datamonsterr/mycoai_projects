from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import SystemState

DEFAULT_THRESHOLD = 20
COUNTER_KEY = "retraining_counter"
COUNTER_FIELDS = ("images_added", "bbox_corrections", "items_archived", "species_added")


async def _ensure_counter(db: AsyncSession) -> SystemState:
    result = await db.execute(select(SystemState).where(SystemState.key == COUNTER_KEY))
    row = result.scalar_one_or_none()
    if row is None:
        row = SystemState(
            key=COUNTER_KEY,
            value={
                "images_added": 0,
                "bbox_corrections": 0,
                "items_archived": 0,
                "species_added": 0,
                "last_reset_at": None,
                "threshold": DEFAULT_THRESHOLD,
            },
        )
        db.add(row)
        await db.flush()
    return row


async def get_counter(db: AsyncSession) -> dict[str, Any]:
    row = await _ensure_counter(db)
    return dict(row.value)


async def increment_counter(
    db: AsyncSession, field: str, amount: int = 1
) -> dict[str, Any]:
    if field not in COUNTER_FIELDS:
        raise ValueError(f"Unknown counter field: {field}")
    row = await _ensure_counter(db)
    current = int(row.value.get(field, 0))  # type: ignore[call-overload]
    row.value[field] = current + amount
    row.updated_at = datetime.datetime.now(datetime.UTC)
    await db.flush()
    return dict(row.value)


async def reset_counter(db: AsyncSession) -> dict[str, Any]:
    row = await _ensure_counter(db)
    for fld in COUNTER_FIELDS:
        row.value[fld] = 0
    row.value["last_reset_at"] = datetime.datetime.now(datetime.UTC).isoformat()
    row.updated_at = datetime.datetime.now(datetime.UTC)
    await db.flush()
    return dict(row.value)


async def get_threshold(db: AsyncSession) -> int:
    row = await _ensure_counter(db)
    return int(row.value.get("threshold", DEFAULT_THRESHOLD))  # type: ignore[call-overload]
