from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.dependencies import CurrentUser
from ..core.exceptions import NotFoundError
from ..database import get_db
from ..models import Image, RetrievalJob, RetrievalNeighbor, RetrievalResult, Segment
from ..qdrant.aggregation import aggregate_predictions
from ..qdrant.client import get_collection_name, get_qdrant_client
from ..qdrant.models import FilterSpec, NeighborResult, QueryResult
from ..qdrant.operations import query_points_by_id
from ..repos.strain import StrainRepository
from ..schemas import (
    RetrievalJobResponse,
    RetrievalQueryRequest,
    RetrievalResultsResponse,
)
from ..services.stores import utcnow

router = APIRouter()


def _parse_uuid(value: str, resource: str = "Resource") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as err:
        raise NotFoundError(f"{resource} '{value}' not found") from err


def _strain_to_species_map(
    db_neighbors: list, strain_repo: StrainRepository
) -> dict[str, str]:
    strain_names = {n.get("strain") for n in db_neighbors if n.get("strain")}
    return {s: s for s in strain_names if s}


async def _resolve_species_name(db: AsyncSession, strain_name: str) -> str:
    from ..models import Species, Strain

    result = await db.execute(
        select(Species.name)
        .join(Strain, Strain.species_id == Species.id)
        .where(Strain.name == strain_name)
    )
    row = result.scalar_one_or_none()
    return row if row else strain_name


def _get_filter_spec(image: Image, environment_strategy: str) -> FilterSpec:
    if environment_strategy == "same_media" and image.media is not None:
        return FilterSpec(environment=image.media.name, environment_strategy=environment_strategy)
    return FilterSpec(environment_strategy=environment_strategy)


@router.post("/query", response_model=RetrievalJobResponse, status_code=202)
async def start_query(
    data: RetrievalQueryRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    image_uuid = _parse_uuid(data.image_id, "Image")
    image = await db.scalar(
        select(Image)
        .options(selectinload(Image.media))
        .where(Image.id == image_uuid)
    )
    if image is None:
        raise NotFoundError(f"Image {data.image_id} not found")

    segments = (
        await db.execute(
            select(Segment).where(
                Segment.image_id == image_uuid,
                Segment.is_archived.is_(False),
            )
        )
    ).scalars().all()

    if not segments:
        raise NotFoundError(f"No active segments found for image {data.image_id}")

    job = RetrievalJob(
        user_id=user.id,
        job_type="single",
        status="processing",
        config={
            "image_id": data.image_id,
            "k": data.k,
            "aggregation": data.aggregation,
            "environment_strategy": data.environment_strategy,
            "research_verified_default": "freq_strength+same_media+EfficientNetB1_finetuned",
            "segment_count": len(segments),
        },
    )
    db.add(job)
    await db.flush()

    try:
        qdrant = get_qdrant_client()
        collection = get_collection_name()
        all_neighbors: list[NeighborResult] = []
        raw_results: list[dict[str, object]] = []
        filter_spec = _get_filter_spec(image, data.environment_strategy)

        for seg in segments:
            if seg.qdrant_point_id is None:
                continue
            point_id = seg.qdrant_point_id.int
            try:
                result: QueryResult = query_points_by_id(
                    qdrant,
                    point_id,
                    k=data.k,
                    filter_spec=filter_spec,
                    exclude_self=True,
                    exclude_siblings=True,
                    collection_name=collection,
                )
            except (ValueError, RuntimeError):
                continue

            seg_neighbors: list[dict[str, object]] = []
            for neighbor in result.neighbors:
                species = await _resolve_species_name(db, neighbor.strain or "unknown")
                seg_neighbors.append(
                    {
                        "specy": species,
                        "score": neighbor.score,
                        "strain": neighbor.strain,
                        "extractor": neighbor.extractor or "default",
                        "environment": neighbor.environment,
                        "image_id": neighbor.image_id,
                    }
                )
                all_neighbors.append(neighbor)
            if seg_neighbors:
                raw_results.append({"neighbors": seg_neighbors})

        if not raw_results:
            job.status = "completed"
            job.completed_at = utcnow()
            await db.flush()
            return {
                "job_id": str(job.id),
                "status": "completed",
                "estimated_seconds": 0,
            }

        strain_map = _strain_to_species_map(
            [{"strain": n.strain} for n in all_neighbors],
            StrainRepository(),
        )

        aggregation_result = aggregate_predictions(
            raw_results,
            strain_to_specy=strain_map,
            k=data.k,
            strategy=data.aggregation,
        )

        rankings: list[object] = []
        for rank_entry in aggregation_result.ranking:
            rank_neighbors = [
                n
                for n in all_neighbors
                if (_resolve_species_sync(n, strain_map)) == rank_entry.species
            ][:5]

            neighbors_list = []
            for n in rank_neighbors:
                species = _resolve_species_sync(n, strain_map)
                neighbors_list.append(
                    RetrievalNeighbor(
                        neighbor_image_id=n.image_id,
                        neighbor_strain=n.strain or "unknown",
                        neighbor_species=species,
                        similarity=round(n.score, 4),
                        media=n.environment or "unknown",
                        segment_index=n.segment_index or 0,
                    )
                )

            retrieval_result = RetrievalResult(
                job_id=job.id,
                strain_name=image.strain.name if image.strain else "unknown",
                rank=len(rankings) + 1,
                species_name=rank_entry.species,
                score=rank_entry.score,
                neighbors=neighbors_list,
            )
            db.add(retrieval_result)
            rankings.append(rank_entry)

        job.status = "completed"
        job.completed_at = utcnow()
        await db.flush()
        await db.commit()

    except Exception:
        job.status = "failed"
        await db.flush()
        await db.commit()
        raise

    return {
        "job_id": str(job.id),
        "status": job.status,
        "estimated_seconds": 5,
    }


def _resolve_species_sync(neighbor: NeighborResult, strain_map: dict[str, str]) -> str:
    specy = neighbor.specy
    if not specy or specy == "unknown":
        specy = strain_map.get(neighbor.strain or "", "unknown")
    return specy or "unknown"


@router.get("/jobs/{job_id}", response_model=RetrievalJobResponse)
async def get_job_status(
    job_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    job_uuid = _parse_uuid(job_id, "Job")
    job = await db.scalar(
        select(RetrievalJob).where(RetrievalJob.id == job_uuid)
    )
    if not job:
        raise NotFoundError(f"Job {job_id} not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "estimated_seconds": 0,
    }


@router.get("/jobs/{job_id}/results", response_model=RetrievalResultsResponse)
async def get_job_results(
    job_id: str,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    job_uuid = _parse_uuid(job_id, "Job")
    job = await db.scalar(
        select(RetrievalJob).where(RetrievalJob.id == job_uuid)
    )
    if not job:
        raise NotFoundError(f"Job {job_id} not found")

    results = (
        await db.execute(
            select(RetrievalResult)
            .where(RetrievalResult.job_id == job_uuid)
            .order_by(RetrievalResult.rank)
        )
    ).scalars().all()

    rankings = []
    for r in results:
        neighbors_data = await db.execute(
            select(RetrievalNeighbor).where(
                RetrievalNeighbor.result_id == r.id
            ).limit(5)
        )
        neighbors = neighbors_data.scalars().all()
        rankings.append({
            "rank": r.rank,
            "species": r.species_name,
            "score": round(r.score, 4),
            "neighbors": [
                {
                    "strain": n.neighbor_strain,
                    "species": n.neighbor_species,
                    "similarity": round(n.similarity, 4),
                    "media": n.media,
                    "image_thumbnail_url": (
                        f"/api/v1/images/{n.neighbor_image_id}/source"
                        if n.neighbor_image_id
                        else ""
                    ),
                }
                for n in neighbors
            ],
        })

    return {
        "job_id": str(job.id),
        "status": job.status,
        "strain": results[0].strain_name if results else "unknown",
        "rankings": rankings,
    }


@router.post("/query-sync", response_model=RetrievalResultsResponse)
async def query_sync(
    data: RetrievalQueryRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    job_result = await start_query(data, user, db)
    job_id = job_result["job_id"]
    return await get_job_results(job_id, user, db)
