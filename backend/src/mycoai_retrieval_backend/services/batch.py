async def enqueue_batch(count: int) -> dict[str, int | str]:
    return {"job_id": "pending", "accepted": count}
