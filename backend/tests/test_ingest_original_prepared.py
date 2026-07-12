import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_original_prepared import discover_original_prepared_images


def test_discover_original_prepared_images_skips_artifacts(tmp_path: Path) -> None:
    angle_dir = tmp_path / "species-a" / "strain-a" / "MEA" / "ob"
    angle_dir.mkdir(parents=True)
    (angle_dir / "plate.jpg").write_bytes(b"jpg")
    (angle_dir / "prepared.jpg").write_bytes(b"jpg")
    (angle_dir / "segments_yolo").mkdir()
    (angle_dir / "segments_yolo" / "segment_0.jpg").write_bytes(b"jpg")

    result = discover_original_prepared_images(tmp_path)

    assert result == [
        {
            "path": str(angle_dir / "plate.jpg"),
            "species": "Species A",
            "strain": "STRAIN A",
            "media": "MEA",
            "angle": "ob",
        }
    ]
