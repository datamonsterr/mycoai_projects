from pydantic import BaseModel


class DashboardStats(BaseModel):
    images: int
    species: int
    feedback_items: int
    training_jobs: int
