from fastapi import APIRouter, Depends

from ..core.dependencies import CurrentOwner, get_current_user
from ..schemas import (
    TrainingDeployRequest,
    TrainingJobItem,
    TrainingStatus,
    TrainingTriggerRequest,
)
from ..services.stores import get_training_store, new_id, utcnow

router = APIRouter()


@router.get("/status", response_model=TrainingStatus)
def get_training_status(user: dict = Depends(get_current_user)) -> dict:
    return {
        "model_name": "mycoai-retrieval-v1",
        "version": "0.1.0",
        "status": "idle",
        "deployed_at": None,
    }


@router.get("/jobs")
def list_training_jobs(user: dict = Depends(get_current_user)) -> list[dict]:
    store = get_training_store()
    return list(store.list())


@router.post("/trigger", response_model=TrainingJobItem, status_code=202)
def trigger_training(
    data: TrainingTriggerRequest,
    user: CurrentOwner,
) -> dict:
    job_id = new_id()
    job = {
        "id": job_id,
        "status": "processing",
        "reason": data.reason,
        "started_at": utcnow(),
        "completed_at": None,
    }
    get_training_store().put(job)
    return {
        "id": job_id,
        "status": "processing",
        "started_at": job["started_at"],
        "completed_at": None,
    }


@router.get("/jobs/{job_id}", response_model=TrainingJobItem)
def get_training_job(job_id: str, user: CurrentOwner) -> dict:
    from ..core.exceptions import NotFoundError

    job = get_training_store().get(job_id)
    if not job:
        raise NotFoundError(f"Training job {job_id} not found")
    return {
        "id": job["id"],
        "status": job.get("status", "unknown"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    }


@router.post("/jobs/{job_id}/cancel", response_model=TrainingJobItem)
def cancel_training_job(
    job_id: str, user: CurrentOwner
) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_training_store()
    job = store.get(job_id)
    if not job:
        raise NotFoundError(f"Training job {job_id} not found")
    job["status"] = "cancelled"
    store.put(job)
    return {
        "id": job["id"],
        "status": "cancelled",
        "started_at": job.get("started_at"),
        "completed_at": None,
    }


@router.post("/jobs/{job_id}/deploy", response_model=dict)
def deploy_model(
    job_id: str,
    data: TrainingDeployRequest,
    user: CurrentOwner,
) -> dict:
    from ..core.exceptions import NotFoundError

    store = get_training_store()
    job = store.get(job_id)
    if not job:
        raise NotFoundError(f"Training job {job_id} not found")
    return {"status": "deployed", "job_id": job_id, "model_version": "0.2.0"}


@router.post("/rollback", response_model=dict)
def rollback_model(user: CurrentOwner) -> dict:
    return {"status": "rollback_complete", "previous_version": "0.1.0"}
