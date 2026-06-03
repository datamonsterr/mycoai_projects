from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    filename: str
    status: str


class BatchUploadResponse(BaseModel):
    job_id: str
    accepted: int
