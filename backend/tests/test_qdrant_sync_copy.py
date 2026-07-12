import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.sync_qdrant_to_sql as sync_qdrant_to_sql
from scripts.sync_qdrant_to_sql import _copy_collection_vectors


class _FakeClient:
    def __init__(self, *args, **kwargs) -> None:
        self.calls = []
        self._points_count = 0

    def get_collection(self, name):
        self.calls.append(("get_collection", name))
        return SimpleNamespace(
            config=SimpleNamespace(params=SimpleNamespace(vectors={"v": object()})),
            points_count=self._points_count,
        )

    def recreate_collection(self, **kwargs):
        self.calls.append(("recreate_collection", kwargs))
        self._points_count = 0

    def scroll(self, **kwargs):
        self.calls.append(("scroll", kwargs))
        if not hasattr(self, "_done"):
            self._done = True
            point_a = SimpleNamespace(
                id=1,
                vector={"v": [0.1]},
                payload={"segment_id": "seg-1", "image_id": "wrong"},
            )
            point_b = SimpleNamespace(
                id=2,
                vector={"v": [0.2]},
                payload={
                    "segment_id": "item_0323_seg0",
                    "image_id": "wrong",
                    "segment_index": 0,
                    "segment_path": (
                        "Dataset/full_prepared/spec/strain/crea/ob/"
                        "segments_kmeans/segment_0.jpg"
                    ),
                    "strain": "Strain",
                    "environment": "CREA",
                    "angle": "ob",
                },
            )
            return [point_a, point_b], None
        return [], None

    def upsert(self, **kwargs):
        self.calls.append(("upsert", kwargs))
        self._points_count += len(kwargs["points"])


def test_copy_collection_vectors_skips_points_without_recognized_sql_mapping(
    monkeypatch,
) -> None:
    clients = []

    monkeypatch.setattr(
        sync_qdrant_to_sql,
        "_canonical_species_names",
        lambda: {"spec"},
        raising=False,
    )

    def _factory(*args, **kwargs):
        client = _FakeClient(*args, **kwargs)
        clients.append(client)
        return client

    monkeypatch.setattr(sync_qdrant_to_sql, "QdrantClient", _factory, raising=False)

    stats = _copy_collection_vectors(
        "qdrant-research_fold0",
        "myco_fungi_features_full_finetuned",
        {
            "seg-1": {
                "segment_id": "seg-1",
                "image_id": "img-1",
                "media": "CREA",
            }
        },
        {
            ("strain", "crea", "ob", "0", "segment_0.jpg"): {
                "segment_id": "seg-legacy",
                "image_id": "img-2",
                "media": "CREA",
            }
        },
    )

    assert stats == {
        "vectors_copied": 0,
        "skipped_missing_sql": 2,
        "target_points": 0,
        "sql_segments": 1,
    }
    assert len(clients) == 2
    assert all(call[0] != "upsert" for call in clients[1].calls)
