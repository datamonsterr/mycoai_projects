from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_qdrant_settings
from ..core.dependencies import CurrentUser
from ..core.exceptions import NotFoundError
from ..database import get_db
from ..models import Image, RetrievalJob, RetrievalNeighbor, RetrievalResult, Segment
from ..qdrant.aggregation import aggregate_predictions
from ..qdrant.client import get_collection_name, get_qdrant_client
from ..qdrant.models import FilterSpec, NeighborResult, QueryResult
from ..qdrant.operations import query_points_by_id
from ..schemas import (
    RetrievalJobResponse,
    RetrievalQueryRequest,
    RetrievalResultsResponse,
)
from ..services.stores import utcnow
from ..services.threshold import compute_confidence, is_known_confidence

router = APIRouter()


def _parse_uuid(value: str, resource: str = "Resource") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as err:
        raise NotFoundError(f"{resource} '{value}' not found") from err


async def _strain_to_species_map(
    db_neighbors: list[dict[str, str]], db: AsyncSession
) -> dict[str, str]:
    from ..models import Species, Strain

    strain_names = {n.get("strain") for n in db_neighbors if n.get("strain")}
    if not strain_names:
        return {}

    result = await db.execute(
        select(Strain.name, Species.name)
        .join(Species, Strain.species_id == Species.id)
        .where(Strain.name.in_(strain_names))
    )
    strain_to_species: dict[str, str] = {row[0]: row[1] for row in result.all()}
    return {s: strain_to_species.get(s, s) for s in strain_names}


async def _resolve_species_name(db: AsyncSession, strain_name: str) -> str:
    from ..models import Species, Strain

    result = await db.execute(
        select(Species.name)
        .join(Strain, Strain.species_id == Species.id)
        .where(Strain.name == strain_name)
    )
    row = result.scalar_one_or_none()
    return row if row else strain_name


def _get_filter_spec(image: Image, media_strategy: str) -> FilterSpec:
    if media_strategy == "same_media" and image.media is not None:
        return FilterSpec(media=image.media.name, media_strategy=media_strategy)
    return FilterSpec(media_strategy=media_strategy)


def _segment_crop_url(image_id: uuid.UUID, segment_index: int) -> str:
    return f"/api/v1/images/{image_id}/segments/{segment_index}/crop"


@router.post("/query", response_model=RetrievalJobResponse, status_code=202)
async def start_query(
    data: RetrievalQueryRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    image_ids = getattr(data, "image_ids", None) or [data.image_id]
    image_uuids = [_parse_uuid(image_id, "Image") for image_id in image_ids]
    image_rows = (
        (
            await db.execute(
                select(Image)
                .options(selectinload(Image.media), selectinload(Image.segments), selectinload(Image.strain))
                .where(Image.id.in_(image_uuids))
            )
        )
        .scalars()
        .all()
    )
    images_by_id = {image.id: image for image in image_rows}
    missing_ids = [image_id for image_id, image_uuid in zip(image_ids, image_uuids, strict=False) if image_uuid not in images_by_id]
    if missing_ids:
        raise NotFoundError(f"Image {missing_ids[0]} not found")

    query_images: list[tuple[Image, list[Segment]]] = []
    total_segments = 0
    for image_uuid in image_uuids:
        image = images_by_id[image_uuid]
        segments = [seg for seg in image.segments if not seg.is_archived]
        if not segments:
            raise NotFoundError(f"No active segments found for image {image.id}")
        query_images.append((image, segments))
        total_segments += len(segments)

    primary_image = query_images[0][0]
    primary_image_id = str(primary_image.id)
    primary_strain_name = primary_image.strain.name if primary_image.strain else "unknown"

    job = RetrievalJob(
        user_id=user.id,
        job_type="batch" if len(query_images) > 1 else "single",
        status="processing",
        config={
            "image_id": primary_image_id,
            "image_ids": [str(image.id) for image, _ in query_images],
            "k": data.k,
            "aggregation": data.aggregation,
            "media_strategy": data.media_strategy,
            "research_verified_default": "freq_strength+same_media+EfficientNetB1_finetuned",
            "segment_count": total_segments,
            "query_image_count": len(query_images),
        },
    )
    db.add(job)
    await db.flush()

    try:
        qdrant = get_qdrant_client()
        collection = get_collection_name()
        all_neighbors: list[NeighborResult] = []
        raw_results: list[dict[str, object]] = []
        queried_images: list[dict[str, object]] = []

        for image, segments in query_images:
            filter_spec = _get_filter_spec(image, data.media_strategy)
            image_neighbors: list[NeighborResult] = []
            image_segment_urls = [
                _segment_crop_url(image.id, seg.segment_index)
                for seg in segments[:3]
            ]

            for seg in segments:
                seg_neighbors: list[dict[str, object]] = []

                if seg.qdrant_point_id is not None:
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
                        for neighbor in result.neighbors:
                            species = await _resolve_species_name(
                                db, neighbor.strain or "unknown"
                            )
                            seg_neighbors.append(
                                {
                                    "specy": species,
                                    "score": neighbor.score,
                                    "strain": neighbor.strain,
                                    "extractor": neighbor.extractor or "default",
                                    "media": neighbor.media,
                                    "image_id": neighbor.image_id,
                                }
                            )
                            all_neighbors.append(neighbor)
                            image_neighbors.append(neighbor)
                    except (ValueError, RuntimeError):
                        pass

                if not seg_neighbors:
                    seg_neighbors = await _query_by_crop_image(
                        db, seg, qdrant, collection, filter_spec, data.k
                    )
                    for n in seg_neighbors:
                        neighbor = NeighborResult(
                            image_id=n.get("image_id"),
                            score=float(n.get("score", 0.0)),
                            strain=str(n.get("strain", "")),
                            media=str(n.get("media", "")),
                            specy=str(n.get("specy", "")),
                            extractor=str(n.get("extractor", "")),
                        )
                        all_neighbors.append(neighbor)
                        image_neighbors.append(neighbor)

                if seg_neighbors:
                    raw_results.append({"neighbors": seg_neighbors, "query_image_id": str(image.id)})

            queried_images.append(
                {
                    "image_id": str(image.id),
                    "image_url": f"/api/v1/images/{image.id}/source",
                    "media": image.media.name if image.media else "unknown",
                    "segment_image_urls": image_segment_urls,
                    "neighbors": image_neighbors[: data.k],
                }
            )

        if not raw_results:
            job.status = "completed"
            job.completed_at = utcnow()
            await db.flush()
            await db.commit()
            return {
                "job_id": str(job.id),
                "status": "completed",
                "estimated_seconds": 0,
            }

        strain_map = await _strain_to_species_map(
            [{"strain": n.strain} for n in all_neighbors],
            db,
        )

        aggregation_result = aggregate_predictions(
            raw_results,
            strain_to_specy=strain_map,
            k=data.k,
            strategy=data.aggregation,
        )

        # Compute threshold confidence from neighbor scores
        threshold_result: dict[str, object] = {
            "formula": "gnorm_0_2",
            "confidence": 0.0,
            "threshold": 0.12,
            "is_known": True,
        }
        try:
            all_neighbor_scores = sorted([n.score for n in all_neighbors], reverse=True)
            if all_neighbor_scores:
                threshold_result = is_known_confidence(  # type: ignore[assignment]
                    all_neighbor_scores[:11],
                    formula="gnorm_0_2",
                )
        except Exception:
            pass
        job.config = {
            **job.config,
            "threshold": threshold_result,
            "queried_images": [
                {
                    **query_image,
                    "neighbors": [
                        {
                            "strain": neighbor.strain or "unknown",
                            "species": _resolve_species_sync(neighbor, strain_map),
                            "similarity": round(neighbor.score, 4),
                            "media": neighbor.media or "unknown",
                            "image_thumbnail_url": (
                                f"/api/v1/images/{neighbor.image_id}/source"
                                if neighbor.image_id
                                else ""
                            ),
                        }
                        for neighbor in query_image["neighbors"]
                    ],
                }
                for query_image in queried_images
            ],
        }

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
                        media=n.media or "unknown",
                        segment_index=n.segment_index or 0,
                    )
                )

            retrieval_result = RetrievalResult(
                job_id=job.id,
                strain_name=primary_strain_name,
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


async def _query_by_crop_image(
    db: AsyncSession,
    seg: Segment,
    qdrant,
    collection: str,
    filter_spec: FilterSpec,
    k: int,
) -> list[dict[str, object]]:
    from pathlib import Path

    from ..qdrant.operations import query_points_by_image
    from ..services.feature_extraction import (
        extract_features,
        extract_features_from_bytes,
    )

    crop_path = Path(seg.crop_path)

    # Try to read crop bytes from MinIO storage first
    from ..services.feature_extraction import extract_features_from_bytes

    vectors: dict[str, list[float]] = {}
    if not crop_path.exists():
        # Try MinIO storage via the existing storage service
        try:
            from ..services.storage import create_storage, ObjectStorage
            from ..config import get_storage_settings

            stg = create_storage(get_storage_settings())
            if hasattr(stg, "get_bytes"):
                # Build the MinIO key: {artifact_dir}/segments/segment_{index}.jpg
                artifact_dir = crop_path.parent
                key = f"{artifact_dir.parent.name}/{artifact_dir.name}/segments/{crop_path.name}"
                img_bytes = stg.get_bytes(key)
                if img_bytes is None:
                    # Try alternate key format
                    alt_key = f"{artifact_dir}/segments/{crop_path.name}"
                    img_bytes = stg.get_bytes(alt_key)
                if img_bytes:
                    vectors = extract_features_from_bytes(img_bytes)
        except Exception:
            pass

    if not vectors:
        vectors = extract_features(crop_path)

    config = get_qdrant_settings()
    vector_name = config.default_vector_name

    query_vector = vectors.get(vector_name)
    if not query_vector or all(v == 0.0 for v in query_vector):
        for alt in ["colorhistogram", "colorhistogramhs", "gabor"]:
            v = vectors.get(alt)
            if v and any(x != 0.0 for x in v):
                query_vector = v
                vector_name = alt
                break
        else:
            return []

    try:
        result = query_points_by_image(
            qdrant,
            query_vector,
            feature_type=vector_name,
            k=k,
            filter_spec=filter_spec,
            collection_name=collection,
        )
    except (ValueError, RuntimeError):
        return []

    neighbors: list[dict[str, object]] = []
    for neighbor in result.neighbors:
        species = await _resolve_species_name(db, neighbor.strain or "unknown")
        neighbors.append(
            {
                "specy": species,
                "score": neighbor.score,
                "strain": neighbor.strain,
                "extractor": neighbor.extractor or "default",
                "media": neighbor.media,
                "image_id": neighbor.image_id,
            }
        )
    return neighbors


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
    job = await db.scalar(select(RetrievalJob).where(RetrievalJob.id == job_uuid))
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
    job = await db.scalar(select(RetrievalJob).where(RetrievalJob.id == job_uuid))
    if not job:
        raise NotFoundError(f"Job {job_id} not found")

    results = (
        (
            await db.execute(
                select(RetrievalResult)
                .where(RetrievalResult.job_id == job_uuid)
                .order_by(RetrievalResult.rank)
            )
        )
        .scalars()
        .all()
    )

    rankings = []
    for r in results:
        neighbors_data = await db.execute(
            select(RetrievalNeighbor)
            .where(RetrievalNeighbor.result_id == r.id)
            .limit(5)
        )
        neighbors = neighbors_data.scalars().all()
        rankings.append(
            {
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
            }
        )

    threshold = job.config.get("threshold")
    queried_images = job.config.get("queried_images", [])

    return {
        "job_id": str(job.id),
        "status": job.status,
        "strain": results[0].strain_name if results else "unknown",
        "rankings": rankings,
        "queried_images": queried_images,
        "threshold": threshold,
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
