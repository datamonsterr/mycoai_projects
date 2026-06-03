from fastapi import APIRouter, Depends

from ..core.dependencies import get_current_user
from ..schemas import ChartPoint, DashboardStats, QdrantStatus
from ..services.stores import (
    get_image_store,
    get_species_store,
    get_strain_store,
)

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
def get_stats(user: dict = Depends(get_current_user)) -> dict:
    species = [s for s in get_species_store().list() if not s.get("is_archived", False)]
    strains = [s for s in get_strain_store().list() if not s.get("is_archived", False)]
    images = [i for i in get_image_store().list() if not i.get("is_archived", False)]
    return {
        "species_count": len(species),
        "strains_count": len(strains),
        "images_count": len(images),
    }


@router.get("/charts/species", response_model=list[ChartPoint])
def chart_species(user: dict = Depends(get_current_user)) -> list[dict]:
    species = [s for s in get_species_store().list() if not s.get("is_archived", False)]
    return [{"label": s["name"], "value": 1} for s in species]


@router.get("/charts/media", response_model=list[ChartPoint])
def chart_media(user: dict = Depends(get_current_user)) -> list[dict]:
    return [{"label": "MEA", "value": 10}, {"label": "CYA", "value": 5}]


@router.get("/charts/timeline", response_model=list[ChartPoint])
def chart_timeline(user: dict = Depends(get_current_user)) -> list[dict]:
    return [{"label": "2025-05", "value": 3}]


@router.get("/qdrant-status", response_model=QdrantStatus)
def qdrant_status(user: dict = Depends(get_current_user)) -> dict:
    return {"learned": 120, "unlearned": 35}
