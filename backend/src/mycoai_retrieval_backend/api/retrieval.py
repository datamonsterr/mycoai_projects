from fastapi import APIRouter, Depends

from ..core.dependencies import get_current_user
from ..schemas import (
    RetrievalJobResponse,
    RetrievalQueryRequest,
    RetrievalResultsResponse,
)
from ..services.stores import get_retrieval_job_store, new_id, utcnow

router = APIRouter()


@router.post("/query", response_model=RetrievalJobResponse, status_code=202)
def start_query(
    data: RetrievalQueryRequest, user: dict = Depends(get_current_user)
) -> dict:
    job_id = new_id()
    job = {
        "id": job_id,
        "user_id": user["id"],
        "job_type": "single",
        "status": "processing",
        "config": data.model_dump(),
        "created_at": utcnow(),
    }
    get_retrieval_job_store().put(job)
    return {"job_id": job_id, "status": "processing", "estimated_seconds": 5}


@router.get("/jobs/{job_id}", response_model=RetrievalJobResponse)
def get_job_status(job_id: str, user: dict = Depends(get_current_user)) -> dict:
    from ..core.exceptions import NotFoundError

    job = get_retrieval_job_store().get(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")
    return {
        "job_id": job["id"],
        "status": job.get("status", "unknown"),
        "estimated_seconds": 5,
    }


@router.get("/jobs/{job_id}/results", response_model=RetrievalResultsResponse)
def get_job_results(job_id: str, user: dict = Depends(get_current_user)) -> dict:
    from ..core.exceptions import NotFoundError

    job = get_retrieval_job_store().get(job_id)
    if not job:
        raise NotFoundError(f"Job {job_id} not found")
    return {
        "job_id": job["id"],
        "status": "completed",
        "strain": "DTO 148-D1",
        "rankings": [
            {
                "rank": 1,
                "species": "Penicillium commune",
                "score": 0.87,
                "neighbors": [
                    {
                        "strain": "DTO 148-D2",
                        "species": "Penicillium commune",
                        "similarity": 0.92,
                        "media": "MEA",
                        "image_thumbnail_url": f"/api/v1/images/{new_id()}/thumbnail",
                    }
                ],
            }
        ],
    }


@router.post("/query-sync", response_model=RetrievalResultsResponse)
def query_sync(
    data: RetrievalQueryRequest, user: dict = Depends(get_current_user)
) -> dict:
    job_id = new_id()
    return {
        "job_id": job_id,
        "status": "completed",
        "strain": "DTO 148-D1",
        "rankings": [
            {
                "rank": 1,
                "species": "Penicillium commune",
                "score": 0.87,
                "neighbors": [
                    {
                        "strain": "DTO 148-D2",
                        "species": "Penicillium commune",
                        "similarity": 0.92,
                        "media": "MEA",
                        "image_thumbnail_url": f"/api/v1/images/{new_id()}/thumbnail",
                    }
                ],
            }
        ],
    }
