from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest


def load_dataset_sync_module():
    module_path = Path(__file__).resolve().parents[1] / "dataset_sync.py"
    spec = importlib.util.spec_from_file_location("dataset_sync", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dataset_sync = load_dataset_sync_module()


def test_validate_remote_path_requires_rclone_remote_separator() -> None:
    with pytest.raises(dataset_sync.SyncError):
        dataset_sync.validate_remote_path("drive-folder-without-separator")


def test_resolve_rclone_binary_prefers_path(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "rclone":
            return "/usr/bin/rclone"
        return None

    monkeypatch.setattr(dataset_sync.shutil, "which", fake_which)

    assert dataset_sync.resolve_rclone_binary() == "/usr/bin/rclone"


def test_resolve_rclone_binary_falls_back_to_mise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_which(name: str) -> str | None:
        if name == "mise":
            return "/usr/bin/mise"
        return None

    def fake_run(command):
        return dataset_sync.subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="/home/dat/.local/share/mise/installs/rclone/1.73.4/bin/rclone\n",
            stderr="",
        )

    monkeypatch.setattr(dataset_sync.shutil, "which", fake_which)
    monkeypatch.setattr(dataset_sync, "run_command", fake_run)

    assert dataset_sync.resolve_rclone_binary().endswith("/bin/rclone")


def test_build_transfer_specs_maps_scopes_under_dataset_root(tmp_path: Path) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()

    specs = dataset_sync.build_transfer_specs(
        "import",
        "mydrive:mycoai",
        dataset_root,
        ["original/sample", "segmented_image/new-batch"],
    )

    assert specs[0].source == "mydrive:mycoai/original/sample"
    assert specs[0].destination == str(dataset_root / "original/sample")
    assert specs[1].source == "mydrive:mycoai/segmented_image/new-batch"
    assert specs[1].destination == str(dataset_root / "segmented_image/new-batch")


def test_collect_preview_entries_reports_candidate_counts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()

    specs = dataset_sync.build_transfer_specs(
        "export",
        "mydrive:mycoai",
        dataset_root,
        ["original", "segmented_image"],
    )

    counts = {"original": 4, "segmented_image": 7}

    def fake_count(spec, include_patterns):
        return counts[spec.scope]

    monkeypatch.setattr(dataset_sync, "count_candidates_for_spec", fake_count)
    previews = dataset_sync.collect_preview_entries(specs, [])

    assert [entry.candidate_count for entry in previews] == [4, 7]
    assert previews[0].scope == "original"
    assert previews[1].scope == "segmented_image"


def test_execute_copy_command_raises_on_rclone_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    (dataset_root / "original").mkdir()

    spec = dataset_sync.TransferSpec(
        direction="export",
        scope="original",
        source=str(dataset_root / "original"),
        destination="mydrive:mycoai/original",
        local_path=dataset_root / "original",
        remote_path="mydrive:mycoai/original",
    )

    monkeypatch.setattr(
        dataset_sync, "ensure_sufficient_disk", lambda spec, include: None
    )
    monkeypatch.setattr(
        dataset_sync, "resolve_rclone_binary", lambda: "/usr/bin/rclone"
    )
    monkeypatch.setattr(
        dataset_sync,
        "run_streaming_command",
        lambda command, log_path: (
            1,
            "Transferred:            1 / 2, 50%\nErrors:               1\n",
            "network outage",
        ),
    )
    log_path = tmp_path / "results" / "dataset_sync.log"

    with pytest.raises(dataset_sync.TransferExecutionError) as exc_info:
        dataset_sync.execute_copy_command(spec, [], log_path)

    assert exc_info.value.transferred_count == 1
    assert exc_info.value.error_count == 1


def test_run_streaming_command_streams_output_to_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = iter(
                [
                    "Transferred:            1 / 1, 100%\n",
                    "Errors:               0\n",
                ]
            )

        def __enter__(self) -> "FakeProcess":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def wait(self) -> int:
            return 0

    def fake_popen(*args, **kwargs):
        return FakeProcess()

    monkeypatch.setattr(dataset_sync.subprocess, "Popen", fake_popen)

    log_path = tmp_path / "results" / "stream.log"
    returncode, combined_output, recent_output = dataset_sync.run_streaming_command(
        ["rclone", "copy", "src", "dst", "-P"],
        log_path,
    )

    assert returncode == 0
    assert "Transferred:" in combined_output
    assert "Errors:" in combined_output
    assert "Errors:" in recent_output
    assert "$ rclone copy src dst -P" in log_path.read_text()
    assert "Transferred:            1 / 1, 100%" in capsys.readouterr().out


def test_count_local_candidates_respects_include_patterns(tmp_path: Path) -> None:
    dataset_root = tmp_path / "Dataset"
    nested = dataset_root / "original"
    nested.mkdir(parents=True)
    (nested / "one.jpg").write_text("a")
    (nested / "two.txt").write_text("b")

    count = dataset_sync.count_local_candidates(nested, ["*.jpg"])
    assert count == 1


# ---------------------------------------------------------------------------
# T016 additional coverage: direction guardrails, scope parsing, summaries,
# disk guard, include-pattern filtering, and rclone failure modes.
# ---------------------------------------------------------------------------


def test_join_remote_path_handles_bare_remote_with_scope() -> None:
    assert (
        dataset_sync.join_remote_path("drive:", "original/sample")
        == "drive:original/sample"
    )
    assert dataset_sync.join_remote_path("drive:", "segmented") == "drive:segmented"


def test_join_remote_path_preserves_existing_path_suffix() -> None:
    assert (
        dataset_sync.join_remote_path("drive:mycoai", "original/sample")
        == "drive:mycoai/original/sample"
    )
    assert (
        dataset_sync.join_remote_path("drive:mycoai/", "original/sample")
        == "drive:mycoai/original/sample"
    )


def test_join_remote_path_returns_remote_when_scope_empty() -> None:
    assert dataset_sync.join_remote_path("drive:mycoai", "") == "drive:mycoai"
    assert dataset_sync.join_remote_path("drive:mycoai", "/") == "drive:mycoai"


def test_build_transfer_specs_swaps_source_and_dest_for_export(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    sub = dataset_root / "original"
    sub.mkdir()
    (sub / "a.jpg").write_text("a")

    specs = dataset_sync.build_transfer_specs(
        "export",
        "mydrive:mycoai",
        dataset_root,
        ["original"],
    )

    assert specs[0].direction == "export"
    assert specs[0].source == str(sub)
    assert specs[0].destination == "mydrive:mycoai/original"
    assert specs[0].local_path == sub
    assert specs[0].remote_path == "mydrive:mycoai/original"


def test_validate_transfer_spec_raises_for_missing_export_scope(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()

    spec = dataset_sync.TransferSpec(
        direction="export",
        scope="missing",
        source=str(dataset_root / "missing"),
        destination="mydrive:mycoai/missing",
        local_path=dataset_root / "missing",
        remote_path="mydrive:mycoai/missing",
    )

    with pytest.raises(dataset_sync.SyncError, match="does not exist"):
        dataset_sync.validate_transfer_spec(spec)


def test_validate_transfer_spec_import_creates_parent_dirs(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    new_scope = dataset_root / "original" / "new-sample"

    spec = dataset_sync.TransferSpec(
        direction="import",
        scope="original/new-sample",
        source="mydrive:mycoai/original/new-sample",
        destination=str(new_scope),
        local_path=new_scope,
        remote_path="mydrive:mycoai/original/new-sample",
    )

    dataset_sync.validate_transfer_spec(spec)
    assert new_scope.exists()


def test_parse_rclone_stats_extracts_transferred_and_errors() -> None:
    output = "Transferred:       42 / 100 files\nElapsed time:   10s\nErrors:               3"
    transferred, errors = dataset_sync.parse_rclone_stats(output)
    assert transferred == 42
    assert errors == 3


def test_parse_rclone_stats_handles_no_transfer_yet() -> None:
    output = "Transferred:\nElapsed time:    0s\nErrors:               0"
    transferred, errors = dataset_sync.parse_rclone_stats(output)
    assert transferred is None
    assert errors == 0


def test_parse_rclone_stats_handles_empty_output() -> None:
    transferred, errors = dataset_sync.parse_rclone_stats("")
    assert transferred is None
    assert errors == 0


def test_build_include_args_expands_patterns(tmp_path: Path) -> None:
    args = dataset_sync.build_include_args(["*.jpg", "*.png"])
    assert args == ["--include", "*.jpg", "--include", "*.png"]


def test_build_include_args_empty_when_no_patterns() -> None:
    assert dataset_sync.build_include_args([]) == []
    assert dataset_sync.build_include_args([""]) == ["--include", ""]


def test_include_matches_various_patterns() -> None:
    assert dataset_sync.include_matches("photo.jpg", ["*.jpg"]) is True
    assert dataset_sync.include_matches("photo.PNG", ["*.jpg"]) is False
    assert dataset_sync.include_matches("photo.jpg", ["*.jpg", "*.png"]) is True
    assert dataset_sync.include_matches("photo.txt", ["*.jpg", "*.png"]) is False
    assert dataset_sync.include_matches("photo.jpg", []) is True


def test_include_matches_with_directory_paths() -> None:
    assert dataset_sync.include_matches("original/sample/photo.jpg", ["*.jpg"]) is True
    assert (
        dataset_sync.include_matches("original/sample/photo.jpg", ["original/**/*.jpg"])
        is True
    )


def test_probe_remote_access_raises_on_inaccessible_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        dataset_sync, "resolve_rclone_binary", lambda: "/usr/bin/rclone"
    )

    def fake_run(cmd):
        return dataset_sync.subprocess.CompletedProcess(
            cmd, returncode=1, stdout="", stderr="Access denied"
        )

    monkeypatch.setattr(dataset_sync, "run_command", fake_run)

    with pytest.raises(dataset_sync.SyncError, match="Unable to access"):
        dataset_sync.probe_remote_access("badremote:path")


def test_ensure_sufficient_disk_raises_when_space_insufficient(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    sub = dataset_root / "original"
    sub.mkdir()

    spec = dataset_sync.TransferSpec(
        direction="import",
        scope="original",
        source="mydrive:mycoai/original",
        destination=str(sub),
        local_path=sub,
        remote_path="mydrive:mycoai/original",
    )

    def fake_estimate(spec_, include_patterns):
        return 10**18  # enormous remote size

    def fake_disk_usage(path):
        class FakeUsage:
            free = 1000  # tiny local disk

        return FakeUsage()

    monkeypatch.setattr(dataset_sync, "estimate_remote_size_bytes", fake_estimate)
    monkeypatch.setattr(dataset_sync.shutil, "disk_usage", fake_disk_usage)

    with pytest.raises(dataset_sync.SyncError, match="Insufficient free disk"):
        dataset_sync.ensure_sufficient_disk(spec, [])


def test_ensure_sufficient_disk_silent_when_size_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    sub = dataset_root / "original"
    sub.mkdir()

    spec = dataset_sync.TransferSpec(
        direction="import",
        scope="original",
        source="mydrive:mycoai/original",
        destination=str(sub),
        local_path=sub,
        remote_path="mydrive:mycoai/original",
    )

    def fake_estimate(spec_, include_patterns):
        return None  # unknown size

    monkeypatch.setattr(dataset_sync, "estimate_remote_size_bytes", fake_estimate)

    # Should not raise
    dataset_sync.ensure_sufficient_disk(spec, [])


def test_create_summary_structure_matches_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    summary_dir = tmp_path / "results" / "dataset_sync"

    monkeypatch.setattr(dataset_sync, "results_root", lambda: summary_dir)

    entries = [
        dataset_sync.PreviewEntry(
            scope="original/sample",
            source="mydrive:mycoai/original/sample",
            destination=str(dataset_root / "original/sample"),
            candidate_count=5,
        ),
    ]

    summary = dataset_sync.create_summary(
        command_name="plan",
        direction="import",
        remote="mydrive:mycoai",
        dataset_root=dataset_root,
        preview_only=True,
        entries=entries,
        transferred_count=0,
        skipped_count=5,
        failed_count=0,
        log_path=None,
    )

    assert summary["command"] == "plan"
    assert summary["direction"] == "import"
    assert summary["preview_only"] is True
    assert summary["candidate_count"] == 5
    assert summary["transferred_count"] == 0
    assert summary["skipped_count"] == 5
    assert summary["failed_count"] == 0
    assert len(summary["entries"]) == 1
    assert summary["summary_path"]


def test_run_plan_exit_zero_on_success(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    summary_dir = tmp_path / "results" / "dataset_sync"

    def fake_resolve(path):
        return dataset_root

    monkeypatch.setattr(dataset_sync, "resolve_dataset_root", fake_resolve)
    monkeypatch.setattr(dataset_sync, "ensure_rclone_available", lambda: None)
    monkeypatch.setattr(dataset_sync, "ensure_external_rclone_config", lambda: None)
    monkeypatch.setattr(dataset_sync, "results_root", lambda: summary_dir)

    def fake_probe(remote):
        pass

    monkeypatch.setattr(dataset_sync, "probe_remote_access", fake_probe)

    entries = [
        dataset_sync.PreviewEntry(
            scope=".",
            source="mydrive:mycoai",
            destination=str(dataset_root),
            candidate_count=3,
        ),
    ]

    def fake_collect(specs, include_patterns):
        return entries

    monkeypatch.setattr(dataset_sync, "collect_preview_entries", fake_collect)

    import argparse

    args = argparse.Namespace(
        command="plan",
        direction="import",
        remote="mydrive:mycoai",
        dataset_root=str(dataset_root),
        scope=[],
        include=[],
    )

    exit_code = dataset_sync.run_plan(args)
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Direction: import" in output
    assert "Preview only: True" in output


def test_run_transfer_writes_summary_when_scope_fails_mid_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset_root = tmp_path / "Dataset"
    dataset_root.mkdir()
    summary_dir = tmp_path / "results" / "dataset_sync"

    monkeypatch.setattr(dataset_sync, "ensure_rclone_available", lambda: None)
    monkeypatch.setattr(dataset_sync, "ensure_external_rclone_config", lambda: None)
    monkeypatch.setattr(dataset_sync, "resolve_dataset_root", lambda path: dataset_root)
    monkeypatch.setattr(dataset_sync, "probe_remote_access", lambda remote: None)
    monkeypatch.setattr(dataset_sync, "results_root", lambda: summary_dir)

    specs = [
        dataset_sync.TransferSpec(
            direction="import",
            scope="scope-a",
            source="remote:scope-a",
            destination=str(dataset_root / "scope-a"),
            local_path=dataset_root / "scope-a",
            remote_path="remote:scope-a",
        ),
        dataset_sync.TransferSpec(
            direction="import",
            scope="scope-b",
            source="remote:scope-b",
            destination=str(dataset_root / "scope-b"),
            local_path=dataset_root / "scope-b",
            remote_path="remote:scope-b",
        ),
    ]
    entries = [
        dataset_sync.PreviewEntry(
            scope="scope-a",
            source="remote:scope-a",
            destination=str(dataset_root / "scope-a"),
            candidate_count=2,
        ),
        dataset_sync.PreviewEntry(
            scope="scope-b",
            source="remote:scope-b",
            destination=str(dataset_root / "scope-b"),
            candidate_count=2,
        ),
    ]

    monkeypatch.setattr(dataset_sync, "build_transfer_specs", lambda *args: specs)
    monkeypatch.setattr(dataset_sync, "validate_transfer_spec", lambda spec: None)
    monkeypatch.setattr(dataset_sync, "collect_preview_entries", lambda *args: entries)

    def fake_execute(spec, include_patterns, log_path):
        if spec.scope == "scope-a":
            return 2, 0
        raise dataset_sync.TransferExecutionError(
            spec.scope,
            "network outage",
            transferred_count=1,
            error_count=1,
        )

    monkeypatch.setattr(dataset_sync, "execute_copy_command", fake_execute)

    import argparse
    import json

    args = argparse.Namespace(
        remote="remote:",
        dataset_root=str(dataset_root),
        scope=["scope-a", "scope-b"],
        include=[],
    )

    with pytest.raises(dataset_sync.SyncError, match="Summary path:"):
        dataset_sync.run_transfer("import", "import", args)

    summary_files = sorted(summary_dir.glob("*_import.json"))
    assert len(summary_files) == 1
    summary = json.loads(summary_files[0].read_text())
    assert summary["transferred_count"] == 3
    assert summary["failed_count"] == 1
    assert summary["skipped_count"] == 0
