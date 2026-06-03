from mycoai_retrieval_backend.schemas.training import TrainingJobRead


async def trigger_training(reason: str | None) -> TrainingJobRead:
    return TrainingJobRead(job_id="pending", status="queued", reason=reason)
