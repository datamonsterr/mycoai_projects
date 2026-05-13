import stat
from pathlib import Path

MONOREPO = Path(__file__).resolve().parents[2]


def test_backup_script_exists() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    assert path.exists(), "Missing backup script"


def test_backup_script_is_executable() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    assert path.stat().st_mode & stat.S_IXUSR, "backup.sh must be executable"


def test_backup_script_has_shebang() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    content = path.read_text()
    assert content.startswith("#!/"), "backup.sh must have shebang"
    assert "bash" in content.splitlines()[0], "backup.sh must use bash"


def test_backup_script_handles_pg_dump() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    content = path.read_text()
    assert "pg_dump" in content, "Must include pg_dump"


def test_backup_script_handles_qdrant_snapshot() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    content = path.read_text()
    assert "snapshots" in content, "Must include Qdrant snapshot"


def test_backup_script_handles_rclone() -> None:
    path = MONOREPO / "deploy/scripts/backup.sh"
    content = path.read_text()
    assert "rclone" in content, "Must include rclone sync"
