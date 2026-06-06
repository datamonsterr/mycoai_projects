import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Species
from ..schemas.species import SpeciesCreate, SpeciesUpdate


async def create_species(db: AsyncSession, data: SpeciesCreate) -> Species:
    existing = await db.execute(select(Species).where(Species.name == data.name))
    if existing.scalar_one_or_none():
        from ..core.exceptions import ConflictError
        raise ConflictError(f"Species '{data.name}' already exists")

    species = Species(name=data.name, description=data.description)
    db.add(species)
    await db.commit()
    await db.refresh(species)
    return species


async def get_species(db: AsyncSession, species_id: UUID) -> Species | None:
    result = await db.execute(select(Species).where(Species.id == species_id))
    return result.scalar_one_or_none()


async def list_species(
    db: AsyncSession,
    is_archived: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[Species]:
    result = await db.execute(
        select(Species)
        .where(Species.is_archived == is_archived)
        .order_by(Species.name)
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_species(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Species))
    return result.scalar() or 0


async def update_species(
    db: AsyncSession, species_id: UUID, data: SpeciesUpdate
) -> Species:
    from ..core.exceptions import NotFoundError

    species = await get_species(db, species_id)
    if not species:
        raise NotFoundError(f"Species {species_id} not found")

    if data.name is not None and data.name != species.name:
        existing = await db.execute(
            select(Species).where(Species.name == data.name, Species.id != species_id)
        )
        if existing.scalar_one_or_none():
            from ..core.exceptions import ConflictError
            raise ConflictError(f"Species '{data.name}' already exists")
        species.name = data.name
    if data.description is not None:
        species.description = data.description
    species.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(species)
    return species


async def archive_species(db: AsyncSession, species_id: UUID) -> Species:
    from ..core.exceptions import NotFoundError

    species = await get_species(db, species_id)
    if not species:
        raise NotFoundError(f"Species {species_id} not found")
    species.is_archived = True
    species.archived_at = datetime.datetime.now(datetime.UTC)
    species.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(species)
    return species


async def restore_species(db: AsyncSession, species_id: UUID) -> Species:
    from ..core.exceptions import NotFoundError

    species = await get_species(db, species_id)
    if not species:
        raise NotFoundError(f"Species {species_id} not found")
    species.is_archived = False
    species.archived_at = None
    species.updated_at = datetime.datetime.now(datetime.UTC)
    await db.commit()
    await db.refresh(species)
    return species
