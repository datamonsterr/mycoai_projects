from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import CurrentUser
from ..database import get_db
from ..models import Image, Media, Species, Strain
from ..schemas.dashboard import (
    DashboardStats,
    MediaDistributionItem,
    SpeciesDistributionItem,
)

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
) -> DashboardStats:
    images = (await db.execute(select(func.count()).select_from(Image))).scalar() or 0
    strains = (await db.execute(select(func.count()).select_from(Strain))).scalar() or 0
    species = (
        await db.execute(select(func.count()).select_from(Species))
    ).scalar() or 0
    media = (await db.execute(select(func.count()).select_from(Media))).scalar() or 0
    return DashboardStats(
        total_images=images,
        total_strains=strains,
        total_species=species,
        total_media=media,
    )


@router.get(
    "/charts/species-distribution",
    response_model=list[SpeciesDistributionItem],
)
async def species_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
) -> list[SpeciesDistributionItem]:
    result = await db.execute(
        select(Species.name, func.count(Image.id).label("image_count"))
        .outerjoin(Image, Image.species_id == Species.id)
        .where(Species.is_archived.is_(False))
        .group_by(Species.id, Species.name)
        .order_by(func.count(Image.id).desc())
    )
    rows = result.all()
    return [
        SpeciesDistributionItem(species_name=row.name, image_count=row.image_count)
        for row in rows
    ]


@router.get(
    "/charts/media-distribution",
    response_model=list[MediaDistributionItem],
)
async def media_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
) -> list[MediaDistributionItem]:
    result = await db.execute(
        select(Media.name, func.count(Image.id).label("image_count"))
        .outerjoin(Image, Image.media_id == Media.id)
        .where(Media.is_archived.is_(False))
        .group_by(Media.id, Media.name)
        .order_by(func.count(Image.id).desc())
    )
    rows = result.all()
    return [
        MediaDistributionItem(media_name=row.name, image_count=row.image_count)
        for row in rows
    ]


@router.get(
    "/charts/timeline",
    response_model=list[dict],
)
async def timeline(
    user: CurrentUser,
) -> list[dict]:
    return []


@router.get("/qdrant-status")
async def qdrant_status(
    user: CurrentUser,
) -> dict:
    return {"learned": 0, "unlearned": 0}
