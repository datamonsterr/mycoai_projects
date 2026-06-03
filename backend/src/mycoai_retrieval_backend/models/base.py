from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class BaseModel:
    id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
