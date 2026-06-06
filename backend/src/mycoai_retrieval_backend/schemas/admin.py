from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class UserRoleUpdate(BaseModel):
    role: Literal["user", "owner"]


class UserStatusUpdate(BaseModel):
    is_active: bool


class AdminUserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


class AuditLogResponse(BaseModel):
    id: int
    user_id: str
    action: str
    entity_type: str
    entity_id: str | None = None
    changes: dict | None = None
    ip_address: str | None = None
    created_at: str

    model_config = {"from_attributes": True}
