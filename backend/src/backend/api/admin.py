from __future__ import annotations

import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.dependencies import CurrentOwner, CurrentUser
from ..core.exceptions import ConflictError, NotFoundError, ValidationError
from ..core.security import hash_token
from ..database import get_db
from ..models import AuditLog, InviteToken, User
from ..repos.user import UserRepository
from ..schemas.admin import (
    AdminUserResponse,
    AuditLogResponse,
    InviteUserRequest,
    InviteUserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)

router = APIRouter()

_OWNER_QUOTA_MSG = (
    "Cannot deactivate the last active owner. Promote another user to owner first."
)


def _serialize_user(user: User) -> AdminUserResponse:
    return AdminUserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


def _serialize_audit_log(entry: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=entry.id,
        user_id=str(entry.user_id),
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=str(entry.entity_id) if entry.entity_id else None,
        changes=entry.changes if entry.changes is not None else None,
        ip_address=str(entry.ip_address) if entry.ip_address else None,
        created_at=entry.created_at.isoformat(),
    )


async def _create_audit_entry(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.flush()


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> list[AdminUserResponse]:
    users = await UserRepository.list_users(
        db, role=role, is_active=is_active, offset=offset, limit=limit
    )
    return [_serialize_user(u) for u in users]


@router.post("/users/invite", response_model=InviteUserResponse, status_code=201)
async def invite_user(
    data: InviteUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    request: Request,
) -> InviteUserResponse:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing is not None:
        raise ConflictError("User with this email already exists")
    existing_invite = await db.scalar(
        select(InviteToken).where(InviteToken.email == data.email)
    )
    if existing_invite is not None:
        await db.delete(existing_invite)
        await db.flush()

    token = secrets.token_urlsafe(32)
    settings = get_settings()
    user = User(
        email=data.email,
        password_hash="",
        name=data.email.split("@")[0],
        role="user",
        is_active=False,
    )
    db.add(user)
    await db.flush()

    invite = InviteToken(
        user_id=user.id,
        email=data.email,
        token_hash=hash_token(token),
    )
    db.add(invite)
    await db.flush()

    await _create_audit_entry(
        db,
        user_id=current_owner.id,
        action="invite",
        entity_type="user",
        entity_id=user.id,
        changes={"email": data.email},
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    invite_link = f"{settings.frontend_url}/register?token={token}&email={data.email}"
    return InviteUserResponse(
        user_id=str(user.id),
        email=data.email,
        invite_token=token,
        invite_link=invite_link,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: str,
    data: UserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    request: Request,
) -> AdminUserResponse:
    target = await UserRepository.get_user(db, user_id)
    if target is None:
        raise NotFoundError(f"User {user_id} not found")

    if target.id == current_owner.id:
        raise ValidationError("Cannot change your own role")

    if target.role in ("owner", "dataowner") and data.role == "user":
        active_owners = await UserRepository.count_active_owners(db)
        if active_owners <= 1:
            raise ConflictError(_OWNER_QUOTA_MSG)

    old_role = target.role
    target.role = data.role
    await db.flush()

    await _create_audit_entry(
        db,
        user_id=current_owner.id,
        action="role_change",
        entity_type="user",
        entity_id=target.id,
        changes={"role": {"from": old_role, "to": data.role}},
        ip_address=request.client.host if request.client else None,
    )

    return _serialize_user(target)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: str,
    data: UserStatusUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    request: Request,
) -> AdminUserResponse:
    target = await UserRepository.get_user(db, user_id)
    if target is None:
        raise NotFoundError(f"User {user_id} not found")

    if target.id == current_owner.id:
        raise ValidationError("Cannot change your own status")

    if not data.is_active and target.role in ("owner", "dataowner"):
        active_owners = await UserRepository.count_active_owners(db)
        if active_owners <= 1:
            raise ConflictError(_OWNER_QUOTA_MSG)

    target.is_active = data.is_active
    await db.flush()

    await _create_audit_entry(
        db,
        user_id=current_owner.id,
        action="status_change",
        entity_type="user",
        entity_id=target.id,
        changes={"is_active": data.is_active},
        ip_address=request.client.host if request.client else None,
    )

    return _serialize_user(target)


@router.get("/audit-log", response_model=list[AuditLogResponse])
async def audit_log(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: CurrentUser,
    entity_type: str | None = Query(None),
    entity_id: str | None = Query(None),
    user_id: str | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[AuditLogResponse]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == uuid.UUID(entity_id))
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == uuid.UUID(user_id))
    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [_serialize_audit_log(e) for e in entries]


@router.delete("/test-data", status_code=200)
async def clear_test_data(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_owner: CurrentOwner,
    strain_pattern: str = Query(
        default="TEST%", description="Strain name pattern to match"
    ),
) -> dict:
    from ..models import Image, QdrantIndexState, Segment, Strain

    strains_result = await db.execute(
        select(Strain).where(Strain.name.like(strain_pattern))
    )
    matched_strains = strains_result.scalars().all()
    deleted_images = 0
    deleted_segments = 0

    for strain in matched_strains:
        images_result = await db.execute(
            select(Image).where(Image.strain_id == strain.id)
        )
        images = images_result.scalars().all()
        for img in images:
            segments_result = await db.execute(
                select(Segment).where(Segment.image_id == img.id)
            )
            for seg in segments_result.scalars().all():
                if seg.qdrant_point_id:
                    await db.execute(
                        select(QdrantIndexState).where(
                            QdrantIndexState.segment_id == seg.id
                        )
                    )
                await db.delete(seg)
                deleted_segments += 1
            await db.delete(img)
            deleted_images += 1
        await db.delete(strain)

    await db.commit()
    return {
        "deleted_strains": len(matched_strains),
        "deleted_images": deleted_images,
        "deleted_segments": deleted_segments,
    }
