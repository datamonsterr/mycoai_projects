from datetime import UTC

import pytest
from pydantic import ValidationError

from mycoai_retrieval_backend.schemas.images import (
    BatchUploadResponse,
    ImageUploadResponse,
)
from mycoai_retrieval_backend.schemas.media import (
    MediaCreate,
    MediaListResponse,
    MediaResponse,
    MediaUpdate,
)
from mycoai_retrieval_backend.schemas.retrieval import (
    RetrievalHit,
    RetrievalQuery,
    RetrievalResponse,
)


class TestMediaCreate:
    def test_valid(self) -> None:
        req = MediaCreate(name="Czapek Yeast Autolysate Agar")
        assert req.name == "Czapek Yeast Autolysate Agar"
        assert req.description is None

    def test_with_description(self) -> None:
        req = MediaCreate(name="MEA", description="Malt Extract Agar")
        assert req.name == "MEA"
        assert req.description == "Malt Extract Agar"

    def test_missing_name(self) -> None:
        with pytest.raises(ValidationError):
            MediaCreate()  # type: ignore[arg-type]

    def test_empty_name_allowed(self) -> None:
        req = MediaCreate(name="")
        assert req.name == ""

    def test_description_none_by_default(self) -> None:
        req = MediaCreate(name="PDA")
        assert req.description is None


class TestMediaUpdate:
    def test_full_update(self) -> None:
        req = MediaUpdate(name="New", description="New description")
        assert req.name == "New"
        assert req.description == "New description"

    def test_partial_name_only(self) -> None:
        req = MediaUpdate(name="Renamed")
        assert req.name == "Renamed"
        assert req.description is None

    def test_partial_description_only(self) -> None:
        req = MediaUpdate(description="Only desc")
        assert req.name is None
        assert req.description == "Only desc"

    def test_empty_update_allowed(self) -> None:
        req = MediaUpdate()
        assert req.name is None
        assert req.description is None


class TestMediaResponse:
    def test_from_orm_like_dict(self) -> None:
        from datetime import datetime

        now = datetime.now(UTC)
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "MEA",
            "description": "Malt Extract Agar",
            "is_archived": False,
            "created_at": now,
            "updated_at": now,
        }
        resp = MediaResponse.model_validate(data)
        assert resp.name == "MEA"
        assert resp.is_archived is False

    def test_description_can_be_none(self) -> None:
        from datetime import datetime

        now = datetime.now(UTC)
        resp = MediaResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="CYA",
            description=None,
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        assert resp.description is None


class TestMediaListResponse:
    def test_empty_list(self) -> None:
        resp = MediaListResponse(items=[], total=0)
        assert resp.items == []
        assert resp.total == 0

    def test_with_items(self) -> None:
        from datetime import datetime

        now = datetime.now(UTC)
        item = MediaResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="CYA",
            description=None,
            is_archived=False,
            created_at=now,
            updated_at=now,
        )
        resp = MediaListResponse(items=[item], total=1)
        assert len(resp.items) == 1
        assert resp.total == 1


class TestRetrievalQuery:
    def test_valid_minimal(self) -> None:
        req = RetrievalQuery(query="Penicillium commune")
        assert req.query == "Penicillium commune"
        assert req.limit == 10

    def test_valid_with_limit(self) -> None:
        req = RetrievalQuery(query="Aspergillus", limit=5)
        assert req.query == "Aspergillus"
        assert req.limit == 5

    def test_missing_query(self) -> None:
        with pytest.raises(ValidationError):
            RetrievalQuery()  # type: ignore[arg-type]


class TestRetrievalHit:
    def test_minimal(self) -> None:
        hit = RetrievalHit(id="hit-1", score=0.95)
        assert hit.id == "hit-1"
        assert hit.score == 0.95
        assert hit.species is None

    def test_with_species(self) -> None:
        hit = RetrievalHit(id="hit-2", score=0.88, species="P. expansum")
        assert hit.species == "P. expansum"


class TestRetrievalResponse:
    def test_empty_results(self) -> None:
        resp = RetrievalResponse(query="test", results=[])
        assert resp.query == "test"
        assert resp.results == []

    def test_with_hits(self) -> None:
        hits = [RetrievalHit(id="h1", score=0.9), RetrievalHit(id="h2", score=0.8)]
        resp = RetrievalResponse(query="query", results=hits)
        assert len(resp.results) == 2
        assert resp.results[0].score == 0.9


class TestImageUploadResponse:
    def test_valid(self) -> None:
        resp = ImageUploadResponse(filename="img.jpg", status="ok")
        assert resp.filename == "img.jpg"
        assert resp.status == "ok"


class TestBatchUploadResponse:
    def test_valid(self) -> None:
        resp = BatchUploadResponse(job_id="job-1", accepted=5)
        assert resp.job_id == "job-1"
        assert resp.accepted == 5
