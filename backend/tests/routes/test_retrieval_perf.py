import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from backend.api.retrieval import _resolve_species_fast, start_query
from backend.qdrant.models import NeighborResult, QueryResult


def _neighbor(strain: str, score: float = 0.9) -> NeighborResult:
    return NeighborResult(
        image_id=f"img-{strain}",
        score=score,
        strain=strain,
        media="CYA",
        specy=None,
        segment_index=0,
        extractor="EfficientNetB1_finetuned",
    )


def _build_image(strains: list[str]):
    segs = [
        SimpleNamespace(
            qdrant_point_id=uuid.uuid4(), is_archived=False, segment_index=i
        )
        for i in range(len(strains))
    ]
    return SimpleNamespace(
        id=uuid.uuid4(),
        media=SimpleNamespace(name="CYA"),
        strain=SimpleNamespace(name=strains[0] if strains else "unknown"),
        segments=segs,
    )


def _make_db(image, added_results: list):
    class FakeRows:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    async def fake_execute(stmt, *_a, **_k):
        sql = str(stmt)
        if "FROM images" in sql or '"images"' in sql:
            return FakeRows([image])
        if "FROM strains" in sql and "species" in sql.lower():
            return FakeRows([("DTO 148-F1", "Penicillium chrysogenum")])
        return FakeRows([])

    def fake_add(obj, *_a, **_k):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if obj.__class__.__name__ == "RetrievalResult":
            added_results.append(obj)

    return SimpleNamespace(
        execute=fake_execute,
        add=fake_add,
        flush=_async(),
        commit=_async(),
    )


def _async():
    async def _noop():
        return None

    return _noop


def test_strain_map_bulk_load_is_called_once_per_request():
    db_exec_calls: list[str] = []

    class FakeRows:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return self

        def all(self):
            return self._rows

    image = _build_image(["DTO 148-F1"])

    async def fake_execute(stmt, *_a, **_k):
        sql = str(stmt)
        db_exec_calls.append(sql)
        if "FROM images" in sql:
            return FakeRows([image])
        if "FROM strains" in sql:
            return FakeRows([("DTO 148-F1", "Penicillium chrysogenum")])
        return FakeRows([])

    db = SimpleNamespace(
        execute=fake_execute,
        add=lambda *_a, **_k: None,
        flush=_async(),
        commit=_async(),
    )

    payload = SimpleNamespace(
        image_id=str(image.id),
        k=5,
        aggregation="freq_strength",
        media_strategy="same_media",
    )
    user = SimpleNamespace(id=uuid.uuid4())

    qresult = QueryResult(
        neighbors=[_neighbor("DTO 148-F1") for _ in range(5)],
        total=5,
    )

    with patch("backend.api.retrieval.query_points_by_id", return_value=qresult):
        asyncio.run(start_query(payload, user, db))

    strain_queries = [c for c in db_exec_calls if "FROM strains" in c]
    msg = (
        f"strain->species map must be bulk-loaded once, "
        f"got {len(strain_queries)}: {strain_queries}"
    )
    assert len(strain_queries) == 1, msg


def test_resolve_species_fast_prefers_payload_specy():
    n = _neighbor("DTO 148-F1")
    n.specy = "Penicillium chrysogenum"
    assert _resolve_species_fast(n, {}) == "Penicillium chrysogenum"


def test_resolve_species_fast_falls_back_to_strain_map():
    n = _neighbor("DTO 148-F1")
    n.specy = None
    strain_map = {"DTO 148-F1": "Penicillium chrysogenum"}
    assert _resolve_species_fast(n, strain_map) == "Penicillium chrysogenum"


def test_resolve_species_fast_unknown_when_no_signal():
    n = NeighborResult(image_id="x", score=0.5, strain=None, media="CYA", specy=None)
    assert _resolve_species_fast(n, {}) == "unknown"
