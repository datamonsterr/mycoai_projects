from __future__ import annotations

import csv
import uuid
from pathlib import Path
from typing import Annotated, Any, cast
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
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
from ..services.storage import storage_candidates
from ..services.stores import utcnow
from ..services.threshold import is_known_confidence

router = APIRouter()


def _parse_uuid(value: str, resource: str = "Resource") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError) as err:
        raise NotFoundError(f"{resource} '{value}' not found") from err


def _load_strain_map_from_csv() -> dict[str, str]:
    candidates = [
        Path.cwd() / "Dataset/strain_to_specy.csv",
        Path("/app/Dataset/strain_to_specy.csv"),
    ]
    for path in candidates:
        if not path.exists():
            continue
        with path.open(newline="") as handle:
            return {
                row["Strain"]: row["Species"]
                for row in csv.DictReader(handle)
                if row.get("Strain") and row.get("Species")
            }
    return {}


async def _build_strain_map(db: AsyncSession) -> dict[str, str]:
    """Prefer canonical CSV mapping; fall back to SQL if unavailable."""
    csv_strain_map = _load_strain_map_from_csv()
    if csv_strain_map:
        return csv_strain_map

    from ..models import Species, Strain

    result = await db.execute(
        select(Strain.name, Species.name).join(Species, Strain.species_id == Species.id)
    )
    strain_map: dict[str, str] = {}

    def score_species(name: str) -> tuple[int, int]:
        lower = name.lower()
        if lower.startswith('penicillium '):
            return (3, len(name))
        if lower in {'unknown', 'unknown-species'} or lower.startswith('dto '):
            return (0, len(name))
        return (1, len(name))

    for strain_name, species_name in result.all():
        current = strain_map.get(strain_name)
        if current is None or score_species(species_name) > score_species(current):
            strain_map[strain_name] = species_name
    return strain_map


_SEGMENT_PATH_PREFIX = "segment_path:"


def _resolve_species_fast(neighbor: object, strain_map: dict[str, str]) -> str:
    specy = getattr(neighbor, "specy", None)
    if specy and specy not in {"unknown", "unknown-species"}:
        return specy
    strain = getattr(neighbor, "strain", None)
    if not strain:
        return "unknown"
    return strain_map.get(strain, strain)


def _pack_neighbor_identity(
    image_id: str | None,
    segment_path: str | None,
) -> str | None:
    if image_id:
        return image_id
    if segment_path:
        return f"{_SEGMENT_PATH_PREFIX}{segment_path}"
    return None


def _unpack_neighbor_segment_path(identity: str | None) -> str | None:
    if identity and identity.startswith(_SEGMENT_PATH_PREFIX):
        return identity.removeprefix(_SEGMENT_PATH_PREFIX)
    return None


def _build_neighbor_thumbnail_url(
    image_id: str | None,
    segment_path: str | None = None,
) -> str:
    packed_segment_path = _unpack_neighbor_segment_path(image_id)
    if packed_segment_path:
        return (
            f"/api/v1/retrieval/evidence?segment_path="
            f"{quote(packed_segment_path, safe='')}"
        )
    if image_id:
        return f"/api/v1/images/{image_id}/source"
    if segment_path:
        return f"/api/v1/retrieval/evidence?segment_path={quote(segment_path, safe='')}"
    return ""


def _get_filter_spec(image: Image, media_strategy: str) -> FilterSpec:
    if media_strategy == "same_media" and image.media is not None:
        return FilterSpec(media=image.media.name, media_strategy=media_strategy)
    return FilterSpec(media_strategy=media_strategy)


def _segment_crop_url(image_id: uuid.UUID, segment_index: int) -> str:
    return f"/api/v1/images/{image_id}/segments/{segment_index}/crop"


@router.get("/evidence", response_model=None)
async def get_retrieval_evidence(segment_path: str) -> Response:
    raw_segment_path = unquote(segment_path).strip()
    candidate = Path(raw_segment_path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise HTTPException(status_code=404, detail="retrieval evidence not found")
    if candidate.exists():
        return FileResponse(candidate)

    try:
        from ..config import get_storage_settings
        from ..services.storage import create_storage

        settings = get_storage_settings()
        storage = create_storage(settings)
        upload_root = Path(settings.upload_root)
        if not upload_root.is_absolute():
            upload_root = (Path.cwd() / upload_root).resolve()

        for key in storage_candidates(
            raw_segment_path,
            upload_root=upload_root,
        ):
            data = storage.get_bytes(key)
            if data:
                return Response(content=data, media_type="image/jpeg")
    except Exception as exc:
        raise HTTPException(
            status_code=404,
            detail="retrieval evidence not found",
        ) from exc

    raise HTTPException(status_code=404, detail="retrieval evidence not found")


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
                .options(
                    selectinload(Image.media),
                    selectinload(Image.segments),
                    selectinload(Image.strain),
                )
                .where(Image.id.in_(image_uuids))
            )
        )
        .scalars()
        .all()
    )
    images_by_id = {image.id: image for image in image_rows}
    missing_ids = [
        image_id
        for image_id, image_uuid in zip(image_ids, image_uuids, strict=False)
        if image_uuid not in images_by_id
    ]
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
    primary_strain_name = (
        primary_image.strain.name if primary_image.strain else "unknown"
    )

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
            "research_verified_default": (
                "freq_strength+same_media+EfficientNetB1_finetuned"
            ),
            "segment_count": total_segments,
            "query_image_count": len(query_images),
        },
    )
    db.add(job)
    await db.flush()

    try:
        qdrant = get_qdrant_client()
        collection = get_collection_name()
        strain_map = await _build_strain_map(db)
        all_neighbors: list[NeighborResult] = []
        raw_results: list[dict[str, object]] = []
        queried_images: list[dict[str, Any]] = []

        for image, segments in query_images:
            filter_spec = _get_filter_spec(image, data.media_strategy)
            query_segments: list[dict[str, Any]] = []

            for seg in segments:
                seg_neighbors: list[dict[str, object]] = []
                query_filter_spec = filter_spec.model_copy(deep=True)
                if image.strain is not None:
                    query_filter_spec.exclude_strain = image.strain.name

                if seg.qdrant_point_id is not None:
                    point_id = seg.qdrant_point_id.int
                    try:
                        result: QueryResult = query_points_by_id(
                            qdrant,
                            point_id,
                            k=data.k,
                            filter_spec=query_filter_spec,
                            exclude_self=True,
                            exclude_siblings=True,
                            collection_name=collection,
                        )
                        for neighbor in result.neighbors:
                            species = _resolve_species_fast(neighbor, strain_map)
                            if species in {"unknown", "unknown-species"}:
                                continue
                            seg_neighbors.append(
                                {
                                    "specy": species,
                                    "score": neighbor.score,
                                    "strain": neighbor.strain,
                                    "extractor": neighbor.extractor or "default",
                                    "media": neighbor.media,
                                    "image_id": neighbor.image_id,
                                    "segment_path": neighbor.segment_path,
                                }
                            )
                            all_neighbors.append(neighbor)
                    except (ValueError, RuntimeError):
                        pass

                if not seg_neighbors:
                    crop_filter_spec = filter_spec.model_copy(deep=True)
                    if image.strain is not None:
                        crop_filter_spec.exclude_strain = image.strain.name
                    seg_neighbors = await _query_by_crop_image(
                        seg, qdrant, collection, crop_filter_spec, data.k, strain_map
                    )
                    for n in seg_neighbors:
                        neighbor = NeighborResult(
                            image_id=cast(str | None, n.get("image_id")),
                            score=float(cast(float, n.get("score", 0.0))),
                            strain=str(n.get("strain", "")),
                            media=str(n.get("media", "")),
                            specy=str(n.get("specy", "")),
                            extractor=str(n.get("extractor", "")),
                            segment_path=cast(str | None, n.get("segment_path")),
                        )
                        all_neighbors.append(neighbor)

                if seg_neighbors:
                    raw_results.append(
                        {
                            "neighbors": seg_neighbors,
                            "query_image_id": str(image.id),
                            "segment_index": seg.segment_index,
                        }
                    )
                    query_segments.append(
                        {
                            "segment_index": seg.segment_index,
                            "segment_image_url": _segment_crop_url(
                                image.id, seg.segment_index
                            ),
                            "neighbors": seg_neighbors[: data.k],
                        }
                    )

            queried_images.append(
                {
                    "image_id": str(image.id),
                    "image_url": f"/api/v1/images/{image.id}/source",
                    "media": image.media.name if image.media else "unknown",
                    "segment_image_urls": [
                        item["segment_image_url"] for item in query_segments
                    ],
                    "segments": query_segments,
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
                    "segments": [
                        {
                            **segment,
                            "neighbors": [
                                {
                                    "strain": str(neighbor.get("strain") or "unknown"),
                                    "species": str(neighbor.get("specy") or "unknown"),
                                    "similarity": round(
                                        float(neighbor.get("score", 0.0)), 4
                                    ),
                                    "media": str(neighbor.get("media") or "unknown"),
                                    "image_thumbnail_url": (
                                        _build_neighbor_thumbnail_url(
                                            cast(
                                                str | None,
                                                neighbor.get("image_id"),
                                            ),
                                            cast(
                                                str | None,
                                                neighbor.get("segment_path"),
                                            ),
                                        )
                                    ),
                                }
                                for neighbor in segment["neighbors"]
                            ],
                        }
                        for segment in query_image["segments"]
                    ],
                    "neighbors": [
                        {
                            "strain": str(neighbor.get("strain") or "unknown"),
                            "species": str(neighbor.get("specy") or "unknown"),
                            "similarity": round(float(neighbor.get("score", 0.0)), 4),
                            "media": str(neighbor.get("media") or "unknown"),
                            "image_thumbnail_url": _build_neighbor_thumbnail_url(
                                cast(str | None, neighbor.get("image_id")),
                                cast(str | None, neighbor.get("segment_path")),
                            ),
                        }
                        for segment in query_image["segments"]
                        for neighbor in segment["neighbors"]
                    ],
                }
                for query_image in queried_images
            ],
        }

        rankings: list[object] = []
        for rank_entry in aggregation_result.ranking:
            if rank_entry.species in {"unknown", "unknown-species"}:
                continue
            rank_neighbors = [
                n
                for n in all_neighbors
                if (_resolve_species_sync(n, strain_map)) == rank_entry.species
            ][:5]

            neighbors_list = []
            for rank_neighbor in rank_neighbors:
                species = _resolve_species_sync(rank_neighbor, strain_map)
                neighbors_list.append(
                    RetrievalNeighbor(
                        neighbor_image_id=_pack_neighbor_identity(
                            rank_neighbor.image_id,
                            rank_neighbor.segment_path,
                        ),
                        neighbor_strain=rank_neighbor.strain or "unknown",
                        neighbor_species=species,
                        similarity=round(rank_neighbor.score, 4),
                        media=rank_neighbor.media or "unknown",
                        segment_index=rank_neighbor.segment_index or 0,
                    )
                )

            retrieval_result = RetrievalResult(
                job_id=job.id,
                strain_name=primary_strain_name if len(query_images) == 1 else "batch",
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
    seg: Segment,
    qdrant,
    collection: str,
    filter_spec: FilterSpec,
    k: int,
    strain_map: dict[str, str],
) -> list[dict[str, object]]:
    from pathlib import Path

    from ..qdrant.operations import query_points_by_image
    from ..services.feature_extraction import (
        extract_features,
        extract_features_from_bytes,
    )

    crop_path = Path(seg.crop_path)

    vectors: dict[str, list[float]] = {}
    if not crop_path.exists():
        # Try object storage via the existing storage service.
        try:
            from ..config import get_storage_settings
            from ..services.storage import create_storage

            stg = create_storage(get_storage_settings())
            if hasattr(stg, "get_bytes"):
                candidate_keys: list[str] = []
                marker = "Dataset/uploads/"
                crop_str = str(crop_path)
                if marker in crop_str:
                    candidate_keys.append(crop_str.split(marker, 1)[1])
                candidate_keys.append(str(Path(*crop_path.parts[-5:])))
                candidate_keys.append(str(Path(*crop_path.parts[-4:])))
                candidate_keys.append(str(Path(*crop_path.parts[-3:])))

                for key in candidate_keys:
                    img_bytes = stg.get_bytes(key)
                    if img_bytes:
                        vectors = extract_features_from_bytes(img_bytes)
                        break
        except Exception:
            pass

    if not vectors:
        if not crop_path.exists():
            return []
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
    except Exception:
        return []

    neighbors: list[dict[str, object]] = []
    for neighbor in result.neighbors:
        species = _resolve_species_fast(neighbor, strain_map)
        if species in {"unknown", "unknown-species"}:
            continue
        neighbors.append(
            {
                "specy": species,
                "score": neighbor.score,
                "strain": neighbor.strain,
                "extractor": neighbor.extractor or "default",
                "media": neighbor.media,
                "image_id": neighbor.image_id,
                "segment_path": neighbor.segment_path,
            }
        )
    return neighbors


def _resolve_species_sync(neighbor: NeighborResult, strain_map: dict[str, str]) -> str:
    return _resolve_species_fast(neighbor, strain_map)


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
                        "image_thumbnail_url": _build_neighbor_thumbnail_url(
                            n.neighbor_image_id,
                            getattr(n, "segment_path", None),
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
