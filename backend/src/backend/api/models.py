from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..core.dependencies import CurrentOwner

router = APIRouter()


@router.post("/candidates")
def upload_candidate(user: CurrentOwner) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/candidates/{candidate_id}/evaluate")
def evaluate_candidate(
    candidate_id: str, user: CurrentOwner
) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/candidates/{candidate_id}/promote")
def promote_candidate(
    candidate_id: str, user: CurrentOwner
) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})


@router.post("/candidates/{candidate_id}/reject")
def reject_candidate(
    candidate_id: str, user: CurrentOwner
) -> JSONResponse:
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})
