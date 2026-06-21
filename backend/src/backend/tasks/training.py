async def run(job_id: str) -> dict[str, str]:
    return {"job_id": job_id, "status": "queued"}
