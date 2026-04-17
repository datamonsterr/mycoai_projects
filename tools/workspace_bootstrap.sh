#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

WORKSPACE_ROOT="${MYCOAI_ROOT:-$DEFAULT_WORKSPACE_ROOT}"
FUNGAL_DIR="${WORKSPACE_ROOT}/fungal-cv-qdrant"
DATASET_ROOT="${WORKSPACE_ROOT}/Dataset"
RESULTS_ROOT="${WORKSPACE_ROOT}/results"
WEIGHTS_ROOT="${WORKSPACE_ROOT}/weights"
NON_INTERACTIVE="false"

log() {
  printf '[workspace-bootstrap] %s\n' "$*"
}

warn() {
  printf '[workspace-bootstrap] WARNING: %s\n' "$*" >&2
}

fail() {
  printf '[workspace-bootstrap] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
Usage: bash tools/workspace_bootstrap.sh <command> [options]

Commands:
  prepare       Prepare a fresh MycoAI workspace on the current machine
  smoke-check   Validate the local workspace layout and fungal-cv-qdrant smoke command
  recover       Revalidate a workspace after reconnect, restart, or replacement
  help          Show this help message

Common options:
  --workspace-root <path>  Override the detected MycoAI workspace root

Prepare options:
  --non-interactive        Skip prompts and keep output suitable for automation

Recover options:
  --instance-id <id>       Vast.ai instance identifier used for reconnection lookup
  --host <host>            Updated SSH host used to reconnect
  --port <port>            Updated SSH port used to reconnect
EOF
}

set_workspace_root() {
  local workspace_root="$1"

  WORKSPACE_ROOT="$workspace_root"
  FUNGAL_DIR="${WORKSPACE_ROOT}/fungal-cv-qdrant"
  DATASET_ROOT="${WORKSPACE_ROOT}/Dataset"
  RESULTS_ROOT="${WORKSPACE_ROOT}/results"
  WEIGHTS_ROOT="${WORKSPACE_ROOT}/weights"
}

parse_workspace_root_option() {
  local workspace_root="$WORKSPACE_ROOT"
  NON_INTERACTIVE="false"

  while (($# > 0)); do
    case "$1" in
      --workspace-root)
        (($# >= 2)) || fail "Missing value for --workspace-root"
        workspace_root="$2"
        shift 2
        ;;
      --non-interactive)
        NON_INTERACTIVE="true"
        shift
        ;;
      *)
        break
        ;;
    esac
  done

  set_workspace_root "$(realpath -m "$workspace_root")"
  REMAINING_ARGS=("$@")
}

require_command() {
  local name="$1"

  command -v "$name" >/dev/null 2>&1 || fail "Required command not found: $name"
}

has_mise_tool() {
  local name="$1"

  command -v mise >/dev/null 2>&1 && mise which "$name" >/dev/null 2>&1
}

verify_repo_layout() {
  [[ -f "${WORKSPACE_ROOT}/mise.toml" ]] || fail "Expected mise.toml at ${WORKSPACE_ROOT}/mise.toml"
  [[ -d "$FUNGAL_DIR" ]] || fail "Expected fungal-cv-qdrant at $FUNGAL_DIR"
  [[ -f "${WORKSPACE_ROOT}/.gitmodules" ]] || warn "No .gitmodules found at ${WORKSPACE_ROOT}; submodule repair will be skipped"
}

ensure_workspace_layout() {
  mkdir -p "$DATASET_ROOT" "$RESULTS_ROOT" "$WEIGHTS_ROOT"
}

repair_submodules() {
  if git -C "$WORKSPACE_ROOT" rev-parse --git-dir >/dev/null 2>&1 && [[ -f "${WORKSPACE_ROOT}/.gitmodules" ]]; then
    log "Syncing git submodules"
    git -C "$WORKSPACE_ROOT" submodule update --init --recursive
  else
    warn "Skipping submodule sync because ${WORKSPACE_ROOT} is not a git checkout with submodules"
  fi
}

run_fungal_sync() {
  log "Syncing fungal-cv-qdrant dependencies with uv"
  uv --directory "$FUNGAL_DIR" sync
}

run_fungal_smoke_command() {
  uv --directory "$FUNGAL_DIR" run python -m src.prepare.init --help >/dev/null
}

print_workspace_summary() {
  log "Workspace summary"
  printf '  workspace_root: %s\n' "$WORKSPACE_ROOT"
  printf '  fungal_dir:     %s\n' "$FUNGAL_DIR"
  printf '  dataset_root:   %s\n' "$DATASET_ROOT"
  printf '  results_root:   %s\n' "$RESULTS_ROOT"
  printf '  weights_root:   %s\n' "$WEIGHTS_ROOT"

  if command -v rclone >/dev/null 2>&1 || has_mise_tool rclone; then
    printf '  rclone:         available\n'
  else
    printf '  rclone:         missing (required for tools/dataset_sync.py)\n'
  fi

  if command -v vastai >/dev/null 2>&1; then
    printf '  vastai:         available\n'
  else
    printf '  vastai:         optional (Vast.ai UI is also supported)\n'
  fi

  printf '  next_steps:     bash tools/workspace_bootstrap.sh smoke-check\n'
}

handle_prepare() {
  parse_workspace_root_option "$@"

  if ((${#REMAINING_ARGS[@]} > 0)); then
    fail "Unknown prepare option: ${REMAINING_ARGS[0]}"
  fi

  require_command git
  require_command mise
  require_command uv

  verify_repo_layout
  repair_submodules
  ensure_workspace_layout

  log "Installing shared toolchain with mise"
  (cd "$WORKSPACE_ROOT" && mise install)

  run_fungal_sync

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    log "Prepare completed in non-interactive mode"
  fi

  print_workspace_summary
}

handle_smoke_check() {
  parse_workspace_root_option "$@"

  if ((${#REMAINING_ARGS[@]} > 0)); then
    fail "Unknown smoke-check option: ${REMAINING_ARGS[0]}"
  fi

  require_command git
  require_command mise
  require_command uv

  verify_repo_layout

  [[ -d "$DATASET_ROOT" ]] || fail "Missing Dataset directory at $DATASET_ROOT"
  [[ -d "$RESULTS_ROOT" ]] || fail "Missing results directory at $RESULTS_ROOT"
  [[ -d "$WEIGHTS_ROOT" ]] || fail "Missing weights directory at $WEIGHTS_ROOT"

  log "Running fungal-cv-qdrant smoke command"
  run_fungal_smoke_command

  log "Workspace smoke-check passed"
  print_workspace_summary
}

handle_recover() {
  parse_workspace_root_option "$@"

  local instance_id=""
  local host=""
  local port=""

  while ((${#REMAINING_ARGS[@]} > 0)); do
    case "${REMAINING_ARGS[0]}" in
      --instance-id)
        ((${#REMAINING_ARGS[@]} >= 2)) || fail "Missing value for --instance-id"
        instance_id="${REMAINING_ARGS[1]}"
        REMAINING_ARGS=("${REMAINING_ARGS[@]:2}")
        ;;
      --host)
        ((${#REMAINING_ARGS[@]} >= 2)) || fail "Missing value for --host"
        host="${REMAINING_ARGS[1]}"
        REMAINING_ARGS=("${REMAINING_ARGS[@]:2}")
        ;;
      --port)
        ((${#REMAINING_ARGS[@]} >= 2)) || fail "Missing value for --port"
        port="${REMAINING_ARGS[1]}"
        REMAINING_ARGS=("${REMAINING_ARGS[@]:2}")
        ;;
      *)
        fail "Unknown recover option: ${REMAINING_ARGS[0]}"
        ;;
    esac
  done

  require_command git
  require_command mise
  require_command uv

  verify_repo_layout
  repair_submodules
  ensure_workspace_layout

  if [[ ! -d "${FUNGAL_DIR}/.venv" ]]; then
    warn "fungal-cv-qdrant virtual environment is missing; re-running uv sync"
    run_fungal_sync
  fi

  if [[ -n "$instance_id" ]]; then
    log "Recovery is tracking Vast.ai instance: $instance_id"
    if command -v vastai >/dev/null 2>&1; then
      log "Use 'vastai show instance $instance_id' locally to refresh SSH connection details if needed"
    else
      warn "Use the Vast.ai UI or local vastai CLI to refresh SSH connection details for instance $instance_id"
    fi
  fi

  if [[ -n "$host" || -n "$port" ]]; then
    log "Updated SSH connection details"
    [[ -n "$host" ]] && printf '  host: %s\n' "$host"
    [[ -n "$port" ]] && printf '  port: %s\n' "$port"
    log "Update your local SSH config before reopening the workspace in VSCode Remote-SSH"
  fi

  handle_smoke_check --workspace-root "$WORKSPACE_ROOT"
}

main() {
  local command="${1:-help}"
  shift || true

  case "$command" in
    prepare)
      handle_prepare "$@"
      ;;
    smoke-check)
      handle_smoke_check "$@"
      ;;
    recover)
      handle_recover "$@"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      usage >&2
      fail "Unknown command: $command"
      ;;
  esac
}

main "$@"
