from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


class SyncError(RuntimeError):
    """Raised when a dataset sync command cannot continue safely."""


@dataclass(frozen=True)
class TransferSpec:
    direction: str
    scope: str
    source: str
    destination: str
    local_path: Path
    remote_path: str


@dataclass(frozen=True)
class PreviewEntry:
    scope: str
    source: str
    destination: str
    candidate_count: int


def workspace_root() -> Path:
    return Path(os.getenv("MYCOAI_ROOT", Path(__file__).resolve().parents[1])).resolve()


def default_dataset_root() -> Path:
    return workspace_root() / "Dataset"


def results_root() -> Path:
    return workspace_root() / "results" / "dataset_sync"


def validate_remote_path(remote: str) -> str:
    remote = remote.strip()
    if not remote or ":" not in remote:
        raise SyncError(
            "Remote path must be an rclone remote like 'drive:folder' or 'drive:'"
        )
    return remote


def join_remote_path(remote: str, scope: str) -> str:
    clean_scope = scope.strip().strip("/")
    if not clean_scope:
        return remote
    if remote.endswith(":"):
        return f"{remote}{clean_scope}"
    return f"{remote.rstrip('/')}/{clean_scope}"


def resolve_dataset_root(path_value: str | None) -> Path:
    path = Path(path_value).resolve() if path_value else default_dataset_root()
    if not path.exists() or not path.is_dir():
        raise SyncError(
            f"Dataset root does not exist or is not a directory: {path}\n"
            "Run 'bash tools/workspace_bootstrap.sh prepare' first."
        )
    return path


def ensure_external_rclone_config() -> None:
    rclone_config = os.getenv("RCLONE_CONFIG")
    if rclone_config:
        config_path = Path(rclone_config).expanduser().resolve()
    else:
        config_path = Path.home() / ".config" / "rclone" / "rclone.conf"

    if not config_path.exists():
        raise SyncError(
            "No external rclone configuration found. Set RCLONE_CONFIG or create "
            f"{config_path}."
        )


def ensure_rclone_available() -> None:
    resolve_rclone_binary()


def resolve_rclone_binary() -> str:
    rclone_binary = shutil.which("rclone")
    if rclone_binary:
        return rclone_binary

    mise_binary = shutil.which("mise")
    if mise_binary:
        result = run_command([mise_binary, "which", "rclone"])
        if result.returncode == 0:
            candidate = result.stdout.strip()
            if candidate:
                return candidate

    raise SyncError(
        "rclone is required for dataset sync but is not installed or discoverable via mise."
    )


def timestamp_slug() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def build_transfer_specs(
    direction: str, remote: str, dataset_root: Path, scopes: list[str]
) -> list[TransferSpec]:
    raw_scopes = scopes or [""]
    specs: list[TransferSpec] = []

    for scope in raw_scopes:
        normalized_scope = scope.strip().strip("/")
        local_path = (
            dataset_root / normalized_scope if normalized_scope else dataset_root
        )
        remote_path = join_remote_path(remote, normalized_scope)

        if direction == "import":
            source = remote_path
            destination = str(local_path)
        else:
            source = str(local_path)
            destination = remote_path

        specs.append(
            TransferSpec(
                direction=direction,
                scope=normalized_scope,
                source=source,
                destination=destination,
                local_path=local_path,
                remote_path=remote_path,
            )
        )

    return specs


def validate_transfer_spec(spec: TransferSpec) -> None:
    if spec.direction == "export" and not spec.local_path.exists():
        raise SyncError(f"Local export scope does not exist: {spec.local_path}")

    if spec.direction == "import":
        spec.local_path.mkdir(parents=True, exist_ok=True)


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False)


def build_include_args(include_patterns: list[str]) -> list[str]:
    args: list[str] = []
    for pattern in include_patterns:
        args.extend(["--include", pattern])
    return args


def probe_remote_access(remote: str) -> None:
    command = [resolve_rclone_binary(), "lsf", remote, "--max-depth", "1"]
    result = run_command(command)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SyncError(f"Unable to access remote path {remote}: {message}")


def count_remote_candidates(remote_path: str, include_patterns: list[str]) -> int:
    command = [
        resolve_rclone_binary(),
        "lsf",
        remote_path,
        "--recursive",
        "--files-only",
    ]
    command.extend(build_include_args(include_patterns))
    result = run_command(command)
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "unknown error"
        raise SyncError(f"Unable to preview remote scope {remote_path}: {message}")
    return sum(1 for line in result.stdout.splitlines() if line.strip())


def include_matches(path: str, include_patterns: list[str]) -> bool:
    if not include_patterns:
        return True
    return any(fnmatch.fnmatch(path, pattern) for pattern in include_patterns)


def count_local_candidates(local_path: Path, include_patterns: list[str]) -> int:
    if local_path.is_file():
        return int(include_matches(local_path.name, include_patterns))
    if not local_path.exists():
        raise SyncError(f"Local path does not exist: {local_path}")

    total = 0
    for file_path in local_path.rglob("*"):
        if file_path.is_file():
            relative_path = file_path.relative_to(local_path).as_posix()
            if include_matches(relative_path, include_patterns):
                total += 1
    return total


def count_candidates_for_spec(spec: TransferSpec, include_patterns: list[str]) -> int:
    if spec.direction == "import":
        return count_remote_candidates(spec.remote_path, include_patterns)
    return count_local_candidates(spec.local_path, include_patterns)


def collect_preview_entries(
    specs: list[TransferSpec], include_patterns: list[str]
) -> list[PreviewEntry]:
    previews: list[PreviewEntry] = []
    for spec in specs:
        candidate_count = count_candidates_for_spec(spec, include_patterns)
        previews.append(
            PreviewEntry(
                scope=spec.scope or ".",
                source=spec.source,
                destination=spec.destination,
                candidate_count=candidate_count,
            )
        )
    return previews


def parse_rclone_stats(output: str) -> tuple[int | None, int]:
    transferred = None
    errors = 0

    transferred_matches = re.findall(r"Transferred:\s+(\d+)(?:\s*/\s*\d+)?", output)
    if transferred_matches:
        transferred = int(transferred_matches[-1])

    errors_match = re.findall(r"Errors:\s+(\d+)", output)
    if errors_match:
        errors = int(errors_match[-1])

    return transferred, errors


def estimate_remote_size_bytes(
    spec: TransferSpec, include_patterns: list[str]
) -> int | None:
    if spec.direction != "import" or include_patterns:
        return None

    command = [resolve_rclone_binary(), "size", spec.remote_path, "--json"]
    result = run_command(command)
    if result.returncode != 0:
        return None

    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return None

    bytes_value = payload.get("bytes")
    return int(bytes_value) if isinstance(bytes_value, int) else None


def ensure_sufficient_disk(spec: TransferSpec, include_patterns: list[str]) -> None:
    estimated_bytes = estimate_remote_size_bytes(spec, include_patterns)
    if estimated_bytes is None:
        return

    free_bytes = shutil.disk_usage(spec.local_path).free
    if estimated_bytes > free_bytes:
        raise SyncError(
            f"Insufficient free disk for import scope {spec.scope or '.'}: "
            f"need {estimated_bytes} bytes, have {free_bytes} bytes."
        )


def append_log(log_path: Path, content: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")


def write_summary(summary: dict[str, object]) -> Path:
    summary_dir = results_root()
    summary_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summary_dir / f"{timestamp_slug()}_{summary['command']}.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary_path


def print_summary(summary: dict[str, object]) -> None:
    print(f"Command: {summary['command']}")
    print(f"Direction: {summary['direction']}")
    print(f"Remote: {summary['remote']}")
    print(f"Dataset root: {summary['dataset_root']}")
    print(f"Preview only: {summary['preview_only']}")
    print("Scopes:")
    for entry in summary["entries"]:
        print(
            f"- {entry['scope']}: {entry['candidate_count']} candidate files\n"
            f"  source={entry['source']}\n"
            f"  destination={entry['destination']}"
        )
    print(
        "Totals: "
        f"candidates={summary['candidate_count']} "
        f"transferred={summary['transferred_count']} "
        f"skipped={summary['skipped_count']} "
        f"failed={summary['failed_count']}"
    )
    if summary.get("log_path"):
        print(f"Log path: {summary['log_path']}")
    print(f"Summary path: {summary['summary_path']}")


def create_summary(
    *,
    command_name: str,
    direction: str,
    remote: str,
    dataset_root: Path,
    preview_only: bool,
    entries: list[PreviewEntry],
    transferred_count: int,
    skipped_count: int,
    failed_count: int,
    log_path: Path | None,
) -> dict[str, object]:
    summary = {
        "command": command_name,
        "direction": direction,
        "remote": remote,
        "dataset_root": str(dataset_root),
        "preview_only": preview_only,
        "candidate_count": sum(entry.candidate_count for entry in entries),
        "transferred_count": transferred_count,
        "skipped_count": skipped_count,
        "failed_count": failed_count,
        "entries": [asdict(entry) for entry in entries],
        "log_path": str(log_path) if log_path else None,
    }
    summary_path = write_summary(summary)
    summary["summary_path"] = str(summary_path)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def execute_copy_command(
    spec: TransferSpec, include_patterns: list[str], log_path: Path
) -> tuple[int, int]:
    ensure_sufficient_disk(spec, include_patterns)
    command = [resolve_rclone_binary(), "copy", spec.source, spec.destination, "-P"]
    command.extend(build_include_args(include_patterns))

    result = run_command(command)
    combined_output = (result.stdout or "") + (result.stderr or "")
    append_log(log_path, f"$ {' '.join(command)}\n{combined_output}")

    if result.returncode != 0:
        message = combined_output.strip() or "unknown error"
        raise SyncError(f"rclone copy failed for {spec.scope or '.'}: {message}")

    transferred_count, error_count = parse_rclone_stats(combined_output)
    return transferred_count or 0, error_count


def run_plan(args: argparse.Namespace) -> int:
    ensure_rclone_available()
    ensure_external_rclone_config()
    remote = validate_remote_path(args.remote)
    dataset_root = resolve_dataset_root(args.dataset_root)
    probe_remote_access(remote)

    specs = build_transfer_specs(args.direction, remote, dataset_root, args.scope)
    for spec in specs:
        validate_transfer_spec(spec)

    entries = collect_preview_entries(specs, args.include)
    summary = create_summary(
        command_name="plan",
        direction=args.direction,
        remote=remote,
        dataset_root=dataset_root,
        preview_only=True,
        entries=entries,
        transferred_count=0,
        skipped_count=sum(entry.candidate_count for entry in entries),
        failed_count=0,
        log_path=None,
    )
    print_summary(summary)
    return 0


def run_transfer(command_name: str, direction: str, args: argparse.Namespace) -> int:
    ensure_rclone_available()
    ensure_external_rclone_config()
    remote = validate_remote_path(args.remote)
    dataset_root = resolve_dataset_root(args.dataset_root)
    probe_remote_access(remote)

    specs = build_transfer_specs(direction, remote, dataset_root, args.scope)
    for spec in specs:
        validate_transfer_spec(spec)

    entries = collect_preview_entries(specs, args.include)
    log_path = results_root() / f"{timestamp_slug()}_{command_name}.log"

    print(
        f"Direction: {direction.upper()}\n"
        f"Remote: {remote}\n"
        f"Dataset root: {dataset_root}\n"
        "Starting non-destructive rclone copy operations..."
    )

    transferred_total = 0
    error_total = 0
    for spec in specs:
        scope_label = spec.scope or "."
        print(f"- Executing scope {scope_label}: {spec.source} -> {spec.destination}")
        transferred_count, error_count = execute_copy_command(
            spec, args.include, log_path
        )
        transferred_total += transferred_count
        error_total += error_count

    candidate_total = sum(entry.candidate_count for entry in entries)
    skipped_total = max(candidate_total - transferred_total, 0)

    summary = create_summary(
        command_name=command_name,
        direction=direction,
        remote=remote,
        dataset_root=dataset_root,
        preview_only=False,
        entries=entries,
        transferred_count=transferred_total,
        skipped_count=skipped_total,
        failed_count=error_total,
        log_path=log_path,
    )
    print_summary(summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preview and execute non-destructive Google Drive dataset transfers."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Preview a proposed transfer")
    plan_parser.add_argument("--direction", choices=["import", "export"], required=True)
    plan_parser.add_argument("--remote", required=True)
    plan_parser.add_argument("--dataset-root")
    plan_parser.add_argument("--scope", action="append", default=[])
    plan_parser.add_argument("--include", action="append", default=[])

    for name in ("import", "export"):
        transfer_parser = subparsers.add_parser(name, help=f"Run a {name} transfer")
        transfer_parser.add_argument("--remote", required=True)
        transfer_parser.add_argument("--dataset-root")
        transfer_parser.add_argument("--scope", action="append", default=[])
        transfer_parser.add_argument("--include", action="append", default=[])

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "plan":
            return run_plan(args)
        if args.command == "import":
            return run_transfer("import", "import", args)
        if args.command == "export":
            return run_transfer("export", "export", args)
        raise SyncError(f"Unsupported command: {args.command}")
    except SyncError as exc:
        print(f"dataset-sync: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
