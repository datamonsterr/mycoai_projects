from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ReindexRequest(BaseModel):
    scope: Literal["changed", "full_active"] = "changed"


class IndexStatusResponse(BaseModel):
    qdrant_index_status: str
    changes_since_last: dict
    external_retraining_recommended: bool
