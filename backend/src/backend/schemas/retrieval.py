from pydantic import BaseModel


class RetrievalQuery(BaseModel):
    query: str
    limit: int = 10


class RetrievalHit(BaseModel):
    id: str
    score: float
    species: str | None = None


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalHit]
