---
description: Autonomous Vast.ai workspace setup — prerequisite check, remote preparation, validation, and VS Code connection
---

You are helping set up a MycoAI workspace on a Vast.ai remote machine. The
canonical entrypoint is `tools/workspace_bootstrap.sh`.

## Prerequisites (check before any automation)

Before running setup commands, verify these prerequisites exist. If any blocker
is missing, stop and report it to the user. Do not attempt workarounds.

### Required (blockers — cannot proceed without)
- [ ] Vast.ai instance is rented and running with SSH access
- [ ] SSH key is attached in the Vast.ai account panel
- [ ] Machine is reachable via SSH (verify with basic SSH connection before
  continuing)
- [ ] Monorepo is cloned on the remote machine (or the agent will clone it)

### Optional (warnings — proceed with reduced functionality)
- [ ] `rclone` is configured (needed for `tools/dataset_sync.py`)
- [ ] `vastai` CLI is available locally (needed to auto-refresh connection
  details)
- [ ] `pnpm` is available (needed for frontend builds)

## Unavoidable Manual Steps

These steps can NOT be automated and must be performed by a human before the
agent can proceed. Call these out explicitly at the start of setup:

1. **Rent Vast.ai instance**: Choose offer with SSH access and enough disk for
   the dataset scope.
2. **Register SSH key**: Attach your public key in the Vast.ai account panel
   before the instance boots.
3. **VS Code host key authorization**: On first VS Code Remote-SSH connect,
   you must accept the remote host's SSH host key.

## Setup Flow

### Step 1: Obtain connection details

Collect these details from the Vast.ai UI or CLI:
- **SSH host** (hostname or IP plus port)
- **SSH user** (usually `root`)
- **Instance ID** (for durable recovery later)

### Step 2: Run workspace preparation

From the monorepo root on the remote machine:

```bash
bash tools/workspace_bootstrap.sh prepare --non-interactive \
  --ssh-host <host> --ssh-user <user> --ssh-port <port> \
  --instance-id <vast-instance-id>
```

This command:
1. Validates host prerequisites (git, mise, uv, repo layout)
2. Reports blockers before making any changes
3. Syncs git submodules
4. Creates shared directories (`Dataset/`, `results/`, `weights/`)
5. Installs shared toolchain with `mise install`
6. Syncs fungal-cv-qdrant dependencies with `uv sync`
7. Prints a structured workspace summary
8. Prints a connection descriptor for VS Code Remote-SSH

### Step 3: Validate the workspace

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

This confirms:
- Shared root directories exist
- Repo layout is valid
- fungal-cv-qdrant smoke command succeeds

### Step 4: Connect from VS Code

After prepare and smoke-check pass, use the printed connection descriptor to:

1. Open VS Code Command Palette (Ctrl+Shift+P)
2. Run: Remote-SSH: Connect to Host...
3. Enter the SSH target from the connection descriptor output
4. Open the workspace root folder on the remote machine
5. Verify file browsing and integrated terminal work

## Completion Criteria

Setup is complete ONLY when all of these are true:
- [ ] `prepare` finished without blockers (prerequisite validation passed)
- [ ] `smoke-check` passed (status: validated)
- [ ] Connection descriptor is printed and contains usable SSH details
- [ ] VS Code opens the correct remote workspace root
- [ ] Integrated terminal is functional on the remote machine
- [ ] Instance ID is recorded for future recovery

## Rerun Safety

The bootstrap script is safe to rerun:
- `prepare` checks prerequisites before mutating the workspace
- Running `prepare` twice does not duplicate or overwrite existing data
- `smoke-check` is a pure validation — always safe to rerun
- Submodule sync is idempotent (`--init --recursive` skips already-present
  submodules)

## Failure Conditions

| Condition | Action |
|-----------|--------|
| Missing git, mise, or uv | Report blocker — these need host installation |
| Missing mise.toml or repos/ | Verify workspace root is the monorepo root |
| SSH connection fails | Verify host/port/user, check instance is running |
| VS Code cannot open remote folder | Verify Remote-SSH extension is installed |
| fungal smoke command fails | Run `uv --directory repos/fungal-cv-qdrant sync` and retry |

## Recovery Entrypoints

When reconnecting to an existing workspace after restart, reconnect, or
replacement:

### Quick Recovery (same host/port)

```bash
bash tools/workspace_bootstrap.sh recover --instance-id <instance-id>
```

### Recovery with Updated Connection Details

If the host or port changed:

```bash
bash tools/workspace_bootstrap.sh recover \
  --instance-id <instance-id> \
  --host <new-host> --port <new-port> --user <user>
```

### Recovery Blockers

Before running recovery, verify:
- [ ] Instance ID is known (from Vast.ai UI or previous setup output)
- [ ] Machine is reachable via the current SSH details
- [ ] Monorepo root still exists on the machine (or re-clone first)

### Recovery Completion Criteria

Same as setup completion criteria plus:
- [ ] Instance ID is confirmed and logged in recovery output
- [ ] Updated connection descriptor reflects current host/port
- [ ] VS Code reopens the workspace using updated descriptor

See also: `/connect-vscode-vastai` for VS Code connection and `/recover-vastai`
for standalone recovery workflow.
