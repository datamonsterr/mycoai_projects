from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.dependencies import CurrentOwner, CurrentUser
from ..database import get_db
from ..models import Strain
from ..schemas.strains import StrainCreate, StrainListResponse, StrainResponse

router = APIRouter()


async def _get_strain(db: AsyncSession, strain_id: UUID) -> Strain | None:
    result = await db.execute(
        select(Strain)
        .options(selectinload(Strain.images), selectinload(Strain.species))
        .where(Strain.id == strain_id)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=StrainListResponse)
async def list_strains(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    species_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
    is_archived: Annotated[bool, Query()] = False,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> StrainListResponse:
    stmt = (
        select(Strain)
        .options(selectinload(Strain.images), selectinload(Strain.species))
        .where(Strain.is_archived == is_archived)
    )
    if species_id:
        stmt = stmt.where(Strain.species_id == species_id)
    if search:
        stmt = stmt.where(Strain.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Strain.name).offset(offset).limit(limit)

    result = await db.execute(stmt)
    strains = list(result.unique().scalars().all())

    count_result = await db.execute(
        select(func.count())
        .select_from(Strain)
        .where(Strain.is_archived == is_archived)
    )
    total = count_result.scalar() or 0

    return StrainListResponse(
        items=[StrainResponse.model_validate(s) for s in strains],
        total=total,
    )


@router.post("", response_model=StrainResponse, status_code=status.HTTP_201_CREATED)
async def create_strain(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    data: StrainCreate,
) -> StrainResponse:
    existing = await db.execute(
        select(Strain).where(
            Strain.name == data.name, Strain.species_id == data.species_id
        )
    )
    if existing.scalar_one_or_none():
        from ..core.exceptions import ConflictError

        raise ConflictError(f"Strain '{data.name}' already exists for this species")

    strain = Strain(
        name=data.name,
        species_id=data.species_id,
        source=data.source,
        is_archived=False,
    )
    db.add(strain)
    await db.commit()
    await db.refresh(strain)
    # Reload with relationships
    strain_obj = await _get_strain(db, strain.id)
    return StrainResponse.model_validate(strain_obj)


@router.get("/{strain_id}", response_model=StrainResponse)
async def get_strain(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
    strain_id: UUID,
) -> StrainResponse:
    from ..core.exceptions import NotFoundError

    strain = await _get_strain(db, strain_id)
    if not strain:
        raise NotFoundError(f"Strain {strain_id} not found")
    return StrainResponse.model_validate(strain)


@router.delete("/{strain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_strain(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentOwner,
    strain_id: UUID,
) -> None:
    from ..core.exceptions import NotFoundError

    strain = await _get_strain(db, strain_id)
    if not strain:
        raise NotFoundError(f"Strain {strain_id} not found")
    strain.is_archived = True
    import datetime

    strain.archived_at = datetime.datetime.now(datetime.UTC)
    strain.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
