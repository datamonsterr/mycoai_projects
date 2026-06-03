from dataclasses import dataclass

from .base import BaseModel


@dataclass
class User(BaseModel):
    email: str = ""
    roles: tuple[str, ...] = ()
    service: str = ""
