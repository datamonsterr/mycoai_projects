#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_WORKSPACE_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

WORKSPACE_ROOT="${MYCOAI_ROOT:-$DEFAULT_WORKSPACE_ROOT}"
  REPOS_DIR="${WORKSPACE_ROOT}/repos"
  FUNGAL_DIR="${REPOS_DIR}/fungal-cv-qdrant"
  DATASET_ROOT="${WORKSPACE_ROOT}/Dataset"

RESULTS_ROOT="${WORKSPACE_ROOT}/results"
WEIGHTS_ROOT="${WORKSPACE_ROOT}/weights"
NON_INTERACTIVE="false"
MODE="first_setup"

CONNECTION_SSH_HOST=""
CONNECTION_SSH_PORT=""
CONNECTION_SSH_USER=""
CONNECTION_INSTANCE_ID=""

BLOCKERS=()
WARNINGS=()

log() {
  printf '[workspace-bootstrap] %s\n' "$*"
}

warn() {
  printf '[workspace-bootstrap] WARNING: %s\n' "$*" >&2
  WARNINGS+=("$*")
}

fail() {
  printf '[workspace-bootstrap] ERROR: %s\n' "$*" >&2
  exit 1
}

blocker() {
  printf '[workspace-bootstrap] BLOCKER: %s\n' "$*" >&2
  BLOCKERS+=("$*")
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
  --non-interactive        Skip prompts and keep output suitable for automation

Prepare options:
  --non-interactive        Skip prompts and keep output suitable for automation

Recover options:
  --instance-id <id>       Vast.ai instance identifier used for reconnection lookup
  --host <host>            Updated SSH host used to reconnect
  --port <port>            Updated SSH port used to reconnect
  --user <user>            SSH username for the remote machine

Connection options (all commands):
  --ssh-host <host>        SSH hostname or IP for connection descriptor output
  --ssh-port <port>        SSH port for connection descriptor output
  --ssh-user <user>        SSH username for connection descriptor output
  --instance-id <id>       Vast.ai instance identifier for durable recovery
EOF
}

set_workspace_root() {
  local workspace_root="$1"

  WORKSPACE_ROOT="$workspace_root"
  REPOS_DIR="${WORKSPACE_ROOT}/repos"
  FUNGAL_DIR="${REPOS_DIR}/fungal-cv-qdrant"

  DATASET_ROOT="${WORKSPACE_ROOT}/Dataset"
  RESULTS_ROOT="${WORKSPACE_ROOT}/results"
  WEIGHTS_ROOT="${WORKSPACE_ROOT}/weights"
}

parse_common_options() {
  WORKSPACE_ROOT_LOCAL="$WORKSPACE_ROOT"
  NON_INTERACTIVE="false"
  CONNECTION_SSH_HOST=""
  CONNECTION_SSH_PORT=""
  CONNECTION_SSH_USER=""
  CONNECTION_INSTANCE_ID=""

  while (($# > 0)); do
    case "$1" in
      --workspace-root)
        (($# >= 2)) || fail "Missing value for --workspace-root"
        WORKSPACE_ROOT_LOCAL="$2"
        shift 2
        ;;
      --non-interactive)
        NON_INTERACTIVE="true"
        shift
        ;;
      --ssh-host)
        (($# >= 2)) || fail "Missing value for --ssh-host"
        CONNECTION_SSH_HOST="$2"
        shift 2
        ;;
      --ssh-port)
        (($# >= 2)) || fail "Missing value for --ssh-port"
        CONNECTION_SSH_PORT="$2"
        shift 2
        ;;
      --ssh-user)
        (($# >= 2)) || fail "Missing value for --ssh-user"
        CONNECTION_SSH_USER="$2"
        shift 2
        ;;
      --instance-id)
        (($# >= 2)) || fail "Missing value for --instance-id"
        CONNECTION_INSTANCE_ID="$2"
        shift 2
        ;;
      *)
        break
        ;;
    esac
  done

  require_command realpath
  set_workspace_root "$(realpath -m "$WORKSPACE_ROOT_LOCAL")"
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

check_command_optional() {
  local name="$1"
  local purpose="$2"

  if command -v "$name" >/dev/null 2>&1 || has_mise_tool "$name"; then
    printf '  %-16s available\n' "$name"
    return 0
  else
    printf '  %-16s missing  (%s)\n' "$name" "$purpose"
    return 1
  fi
}

validate_prerequisites() {
  log "Validating host prerequisites"
  BLOCKERS=()
  WARNINGS=()

  if ! command -v git >/dev/null 2>&1; then
    blocker "git is not installed or not on PATH"
  fi

  if ! command -v mise >/dev/null 2>&1; then
    blocker "mise is not installed or not on PATH"
  fi

  if ! command -v uv >/dev/null 2>&1; then
    blocker "uv is not installed or not on PATH"
  fi

  if ! command -v bash >/dev/null 2>&1; then
    blocker "bash is not available"
  fi

  check_command_optional rclone "required for tools/dataset_sync.py" || \
    warn "rclone is missing; dataset sync commands will not work"

  check_command_optional vastai "useful for refreshing instance connection details" || true

  check_command_optional pnpm "required for frontend builds" || \
    warn "pnpm is missing; frontend build/install commands will fail"

  if [[ ! -f "${WORKSPACE_ROOT}/mise.toml" ]]; then
    blocker "Expected mise.toml at ${WORKSPACE_ROOT}/mise.toml"
  fi

  if [[ ! -d "$REPOS_DIR" ]]; then
    blocker "Expected repos directory at $REPOS_DIR"
  fi

  if [[ ! -d "$FUNGAL_DIR" ]]; then
    blocker "Expected fungal-cv-qdrant at $FUNGAL_DIR"
  fi

  if [[ ! -f "${WORKSPACE_ROOT}/.gitmodules" ]]; then
    warn "No .gitmodules found at ${WORKSPACE_ROOT}; submodule repair will be skipped"
  fi

  local blocker_count=${#BLOCKERS[@]}

  if (( blocker_count > 0 )); then
    printf '\n'
    log "Prerequisite validation FAILED — %d blocker(s) found" "$blocker_count"
    for b in "${BLOCKERS[@]}"; do
      printf '  [BLOCKER] %s\n' "$b"
    done
    return 1
  fi

  if ((${#WARNINGS[@]} > 0)); then
    printf '\n'
    for w in "${WARNINGS[@]}"; do
      printf '  [WARNING] %s\n' "$w"
    done
  fi

  log "Prerequisite validation passed"
  return 0
}

verify_repo_layout() {
  [[ -f "${WORKSPACE_ROOT}/mise.toml" ]] || fail "Expected mise.toml at ${WORKSPACE_ROOT}/mise.toml"
  [[ -d "$REPOS_DIR" ]] || fail "Expected repos directory at $REPOS_DIR"
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

print_connection_descriptor() {
  if [[ -z "$CONNECTION_SSH_HOST" ]]; then
    return 0
  fi

  printf '\n'
  log "Connection descriptor (VS Code Remote-SSH)"
  printf '  ssh_target:   %s\n' "${CONNECTION_SSH_USER:+${CONNECTION_SSH_USER}@}${CONNECTION_SSH_HOST}${CONNECTION_SSH_PORT:+ -p ${CONNECTION_SSH_PORT}}"
  printf '  remote_path:  %s\n' "$WORKSPACE_ROOT"
  printf '\n'

  if [[ -n "$CONNECTION_INSTANCE_ID" ]]; then
    printf '  instance_id:  %s\n' "$CONNECTION_INSTANCE_ID"
  fi

  printf '  source:       %s\n' "$([[ -n "${CONNECTION_SSH_HOST}" ]] && echo 'provided' || echo 'discovered')"
  printf '  descriptor_format: vscode_instructions\n'
  printf '\n'
  printf '  VS Code Remote-SSH steps:\n'
  printf '    1. Open VS Code Command Palette (Ctrl+Shift+P)\n'
  printf '    2. Run: Remote-SSH: Connect to Host...\n'

  local ssh_target="${CONNECTION_SSH_USER}@${CONNECTION_SSH_HOST}"
  if [[ -n "${CONNECTION_SSH_PORT:-}" ]]; then
    printf '    3. Enter: ssh %s -p %s\n' "$ssh_target" "$CONNECTION_SSH_PORT"
  else
    printf '    3. Enter: ssh %s\n' "$ssh_target"
  fi

  printf '    4. Open folder: %s\n' "$WORKSPACE_ROOT"
  printf '    5. Verify file browsing and integrated terminal work\n'
}

print_workspace_summary() {
  log "Workspace summary"
  printf '  mode:           %s\n' "$MODE"
  printf '  status:         %s\n' "${STATUS:-prepared}"
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

  if [[ -n "${CONNECTION_INSTANCE_ID:-}" ]]; then
    printf '  instance_id:    %s\n' "$CONNECTION_INSTANCE_ID"
  fi

  printf '\n'
  log "Next steps"

  if [[ "$MODE" == "first_setup" ]]; then
    printf '  1. Validate:    bash tools/workspace_bootstrap.sh smoke-check\n'
    printf '  2. For VS Code, pass connection details:\n'
    printf '                  bash tools/workspace_bootstrap.sh prepare --ssh-host <host> --ssh-user <user> [--ssh-port <port>]\n'
  elif [[ "$MODE" == "recovery" ]]; then
    printf '  1. Reopen VS Code with the connection details shown above\n'
    printf '  2. To refresh with updated host/port:\n'
    printf '                  bash tools/workspace_bootstrap.sh recover --instance-id %s --host <host> --port <port>\n' \
      "${CONNECTION_INSTANCE_ID:-<id>}"
  fi
}

handle_prepare() {
  parse_common_options "$@"

  if ((${#REMAINING_ARGS[@]} > 0)); then
    fail "Unknown prepare option: ${REMAINING_ARGS[0]}"
  fi

  MODE="first_setup"
  STATUS="pending"

  require_command git
  require_command mise
  require_command uv

  validate_prerequisites || exit 1

  verify_repo_layout
  repair_submodules
  ensure_workspace_layout

  log "Installing shared toolchain with mise"
  (cd "$WORKSPACE_ROOT" && mise install)

  run_fungal_sync

  STATUS="prepared"

  if [[ "$NON_INTERACTIVE" == "true" ]]; then
    log "Prepare completed in non-interactive mode"
  fi

  print_workspace_summary
  print_connection_descriptor
}

handle_smoke_check() {
  parse_common_options "$@"

  if ((${#REMAINING_ARGS[@]} > 0)); then
    fail "Unknown smoke-check option: ${REMAINING_ARGS[0]}"
  fi

  MODE="first_setup"
  STATUS="pending"

  require_command git
  require_command mise
  require_command uv

  verify_repo_layout

  [[ -d "$DATASET_ROOT" ]] || fail "Missing Dataset directory at $DATASET_ROOT"
  [[ -d "$RESULTS_ROOT" ]] || fail "Missing results directory at $RESULTS_ROOT"
  [[ -d "$WEIGHTS_ROOT" ]] || fail "Missing weights directory at $WEIGHTS_ROOT"

  log "Running fungal-cv-qdrant smoke command"
  run_fungal_smoke_command

  STATUS="validated"
  log "Workspace smoke-check passed"
  print_workspace_summary
}

handle_recover() {
  parse_common_options "$@"

  local instance_id="${CONNECTION_INSTANCE_ID}"
  local host="${CONNECTION_SSH_HOST}"
  local port="${CONNECTION_SSH_PORT:-}"

  while ((${#REMAINING_ARGS[@]} > 0)); do
    case "${REMAINING_ARGS[0]}" in
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
      --user)
        ((${#REMAINING_ARGS[@]} >= 2)) || fail "Missing value for --user"
        CONNECTION_SSH_USER="${REMAINING_ARGS[1]}"
        REMAINING_ARGS=("${REMAINING_ARGS[@]:2}")
        ;;
      --instance-id)
        ((${#REMAINING_ARGS[@]} >= 2)) || fail "Missing value for --instance-id"
        instance_id="${REMAINING_ARGS[1]}"
        CONNECTION_INSTANCE_ID="${REMAINING_ARGS[1]}"
        REMAINING_ARGS=("${REMAINING_ARGS[@]:2}")
        ;;
      *)
        fail "Unknown recover option: ${REMAINING_ARGS[0]}"
        ;;
    esac
  done

  MODE="recovery"
  STATUS="pending"

  require_command git
  require_command mise
  require_command uv

  validate_prerequisites || exit 1

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

  if [[ -n "$host" ]]; then
    CONNECTION_SSH_HOST="$host"
  fi
  if [[ -n "${port:-}" ]]; then
    CONNECTION_SSH_PORT="$port"
  fi

  if [[ -n "$host" || -n "${port:-}" ]]; then
    log "Updated SSH connection details"
    [[ -n "$host" ]] && printf '  host: %s\n' "$host"
    [[ -n "${port:-}" ]] && printf '  port: %s\n' "$port"
  fi

  log "Running smoke validation"
  [[ -d "$DATASET_ROOT" ]] || fail "Missing Dataset directory at $DATASET_ROOT"
  [[ -d "$RESULTS_ROOT" ]] || fail "Missing results directory at $RESULTS_ROOT"
  [[ -d "$WEIGHTS_ROOT" ]] || fail "Missing weights directory at $WEIGHTS_ROOT"
  run_fungal_smoke_command

  STATUS="validated"
  log "Recovery validation passed"
  print_workspace_summary
  print_connection_descriptor
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
