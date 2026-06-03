from pydantic import BaseModel


class SpeciesCreate(BaseModel):
    name: str
    description: str | None = None


class SpeciesRead(BaseModel):
    id: str
    name: str
