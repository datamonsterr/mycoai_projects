from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from ..core.security import hash_password


def new_id() -> str:
    return str(uuid4())


class MemoryStore:
    def __init__(self) -> None:
        self.items: dict[str, dict[str, Any]] = {}

    def list(self) -> list[dict[str, Any]]:
        return list(self.items.values())

    def get(self, item_id: str) -> dict[str, Any] | None:
        return self.items.get(item_id)

    def put(self, item: dict[str, Any]) -> dict[str, Any]:
        self.items[item["id"]] = item
        return item

    def remove(self, item_id: str) -> dict[str, Any] | None:
        return self.items.pop(item_id, None)


_user_store = MemoryStore()
_species_store = MemoryStore()
_strain_store = MemoryStore()
_image_store = MemoryStore()
_segment_store = MemoryStore()
_retrieval_job_store = MemoryStore()
_feedback_store = MemoryStore()
_training_store = MemoryStore()
_admin_audit_store = MemoryStore()
_refresh_token_store = MemoryStore()


def utcnow() -> datetime:
    return datetime.now(UTC)


def seed_data() -> None:
    if _user_store.items:
        return
    owner = {
        "id": new_id(),
        "email": "owner@mycoai.dev",
        "password_hash": hash_password("password123"),
        "name": "Owner",
        "role": "owner",
        "is_active": True,
        "created_at": utcnow(),
    }
    user = {
        "id": new_id(),
        "email": "user@mycoai.dev",
        "password_hash": hash_password("password123"),
        "name": "User",
        "role": "user",
        "is_active": True,
        "created_at": utcnow(),
    }
    _user_store.put(owner)
    _user_store.put(user)
    species = {
        "id": new_id(),
        "name": "Penicillium commune",
        "description": "Seed species",
        "is_archived": False,
        "created_at": utcnow(),
        "updated_at": utcnow(),
    }
    _species_store.put(species)
    strain = {
        "id": new_id(),
        "name": "DTO 148-D1",
        "species_id": species["id"],
        "source": "curated_primary",
        "is_archived": False,
        "created_at": utcnow(),
        "updated_at": utcnow(),
        "images": [],
    }
    _strain_store.put(strain)
    image = {
        "id": new_id(),
        "strain_id": strain["id"],
        "strain": strain["name"],
        "media": "MEA",
        "status": "pending_segmentation",
        "file_path": "images/dto-148-d1.png",
        "is_archived": False,
        "created_at": utcnow(),
    }
    _image_store.put(image)


seed_data()


def get_user_store() -> MemoryStore:
    return _user_store


def get_species_store() -> MemoryStore:
    return _species_store


def get_strain_store() -> MemoryStore:
    return _strain_store


def get_image_store() -> MemoryStore:
    return _image_store


def get_segment_store() -> MemoryStore:
    return _segment_store


def get_retrieval_job_store() -> MemoryStore:
    return _retrieval_job_store


def get_feedback_store() -> MemoryStore:
    return _feedback_store


def get_training_store() -> MemoryStore:
    return _training_store


def get_admin_audit_store() -> MemoryStore:
    return _admin_audit_store


def get_refresh_token_store() -> MemoryStore:
    return _refresh_token_store


def find_user_by_email(email: str) -> dict[str, Any] | None:
    return next((user for user in _user_store.list() if user["email"] == email), None)


def create_refresh_token_record(
    user_id: str, token_hash: str, expires_at: datetime
) -> dict[str, Any]:
    item = {
        "id": new_id(),
        "user_id": user_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
        "created_at": utcnow(),
    }
    _refresh_token_store.put(item)
    return item


def revoke_refresh_token(refresh_token: str) -> None:
    for token_id, token in list(_refresh_token_store.items.items()):
        if token["token_hash"] == refresh_token:
            _refresh_token_store.remove(token_id)
            return


def is_first_user() -> bool:
    return len(_user_store.items) == 0


def as_paginated(
    items: Iterable[dict[str, Any]], offset: int, limit: int
) -> tuple[list[dict[str, Any]], int]:
    data = list(items)
    return data[offset : offset + limit], len(data)
