from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import CurrentOwner, CurrentUser
from ..database import get_db
from ..schemas.delete_impact import DeleteImpactResponse
from ..schemas.media import (
    MediaCreate,
    MediaListResponse,
    MediaResponse,
    MediaUpdate,
)

router = APIRouter()


def _repo():
    from ..repos import media as repo

    return repo


@router.get("", response_model=MediaListResponse)
async def list_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    is_archived: Annotated[bool, Query()] = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> MediaListResponse:
    repo = _repo()
    items = await repo.list_media(
        db, is_archived=is_archived, offset=offset, limit=limit
    )
    total = await repo.count_media(db)
    return MediaListResponse(
        items=[MediaResponse.model_validate(m) for m in items],
        total=total,
    )


@router.post("", response_model=MediaResponse, status_code=status.HTTP_201_CREATED)
async def create_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    data: MediaCreate,
) -> MediaResponse:
    repo = _repo()
    media = await repo.create_media(db, data)
    return MediaResponse.model_validate(media)


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    media_id: UUID,
) -> MediaResponse:
    from ..core.exceptions import NotFoundError

    repo = _repo()
    media = await repo.get_media(db, media_id)
    if not media:
        raise NotFoundError(f"Media {media_id} not found")
    return MediaResponse.model_validate(media)


@router.patch("/{media_id}", response_model=MediaResponse)
async def update_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    media_id: UUID,
    data: MediaUpdate,
) -> MediaResponse:
    repo = _repo()
    media = await repo.update_media(db, media_id, data)
    return MediaResponse.model_validate(media)


@router.get("/{media_id}/delete-impact", response_model=DeleteImpactResponse)
async def get_media_delete_impact(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    media_id: UUID,
) -> DeleteImpactResponse:
    repo = _repo()
    strain_count, segment_count = await repo.delete_impact_media(db, media_id)
    return DeleteImpactResponse(
        strain_count=strain_count,
        segment_count=segment_count,
        warning_message=(
            "Archiving this media affects "
            f"{strain_count} strain(s) and {segment_count} segment(s)."
        ),
    )


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    media_id: UUID,
) -> None:
    repo = _repo()
    await repo.archive_media(db, media_id)


@router.post("/{media_id}/restore", response_model=MediaResponse)
async def restore_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    media_id: UUID,
) -> MediaResponse:
    repo = _repo()
    media = await repo.restore_media(db, media_id)
    return MediaResponse.model_validate(media)


@router.delete("/{media_id}/clean", status_code=status.HTTP_204_NO_CONTENT)
async def clean_media(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    media_id: UUID,
) -> None:
    repo = _repo()
    await repo.clean_media(db, media_id)
