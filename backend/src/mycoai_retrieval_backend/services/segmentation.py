async def segment_image(image_id: str) -> dict[str, str]:
    return {"image_id": image_id, "status": "queued"}
