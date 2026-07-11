import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.sync_qdrant_to_sql import scan_original_prepared_media


def test_scan_original_prepared_media_collects_media_dirs(tmp_path: Path) -> None:
    (tmp_path / "penicillium-polonicum" / "dto-148-d1" / "crea" / "ob").mkdir(
        parents=True
    )
    (tmp_path / "penicillium-polonicum" / "dto-148-d1" / "cyas" / "rev").mkdir(
        parents=True
    )
    (tmp_path / "penicillium-polonicum" / "dto-148-d1" / "notes").mkdir(parents=True)

    assert scan_original_prepared_media(tmp_path) == {"CREA", "CYA"}
