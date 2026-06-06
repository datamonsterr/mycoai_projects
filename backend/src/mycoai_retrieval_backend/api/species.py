from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import CurrentOwner, CurrentUser
from ..database import get_db
from ..schemas.species import (
    SpeciesCreate,
    SpeciesListResponse,
    SpeciesResponse,
    SpeciesUpdate,
)

router = APIRouter()


def _repo():
    from ..repos import species as repo
    return repo


@router.get("", response_model=SpeciesListResponse)
async def list_species(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    is_archived: Annotated[bool, Query()] = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SpeciesListResponse:
    repo = _repo()
    items = await repo.list_species(
        db, is_archived=is_archived, offset=offset, limit=limit
    )
    total = await repo.count_species(db)
    return SpeciesListResponse(
        items=[SpeciesResponse.model_validate(s) for s in items],
        total=total,
    )


@router.post("", response_model=SpeciesResponse, status_code=status.HTTP_201_CREATED)
async def create_species(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    data: SpeciesCreate,
) -> SpeciesResponse:
    repo = _repo()
    species = await repo.create_species(db, data)
    return SpeciesResponse.model_validate(species)


@router.get("/{species_id}", response_model=SpeciesResponse)
async def get_species(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    species_id: UUID,
) -> SpeciesResponse:
    from ..core.exceptions import NotFoundError

    repo = _repo()
    species = await repo.get_species(db, species_id)
    if not species:
        raise NotFoundError(f"Species {species_id} not found")
    return SpeciesResponse.model_validate(species)


@router.patch("/{species_id}", response_model=SpeciesResponse)
async def update_species(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    species_id: UUID,
    data: SpeciesUpdate,
) -> SpeciesResponse:
    repo = _repo()
    species = await repo.update_species(db, species_id, data)
    return SpeciesResponse.model_validate(species)


@router.delete("/{species_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_species(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    species_id: UUID,
) -> None:
    repo = _repo()
    await repo.archive_species(db, species_id)
