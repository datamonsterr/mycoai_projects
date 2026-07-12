from pydantic import BaseModel


class DeleteImpactResponse(BaseModel):
    strain_count: int = 0
    image_count: int = 0
    segment_count: int = 0
    warning_message: str
