from pydantic import BaseModel


class TrainingTrigger(BaseModel):
    reason: str | None = None


class TrainingJobRead(BaseModel):
    job_id: str
    status: str
    reason: str | None
