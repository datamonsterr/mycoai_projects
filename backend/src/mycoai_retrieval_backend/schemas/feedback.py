from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    image_id: str
    label: str


class FeedbackItem(BaseModel):
    id: str
    image_id: str
    label: str
