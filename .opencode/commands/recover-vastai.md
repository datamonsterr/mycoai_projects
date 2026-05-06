---
description: Autonomous Vast.ai workspace recovery — revalidate after reconnect, restart, or replacement
---

You are helping recover access to a previously prepared MycoAI workspace on a
Vast.ai remote machine. The canonical entrypoint is `tools/workspace_bootstrap.sh`.

## When to Use Recovery

Use recovery in these scenarios:
- Instance restarted and host/port changed
- Reconnecting after a long pause
- Workspace was prepared before but needs revalidation
- Instance was replaced and the monorepo needs to be re-cloned

## Recovery Flow

### Step 1: Look up the instance

Use the stored instance ID to rediscover current connection details:

```bash
# If vastai CLI is available locally:
vastai show instance <instance-id>

# Otherwise, use the Vast.ai web UI:
# https://cloud.vast.ai → Instances → click the instance → SSH Details
```

### Step 2: Verify SSH connectivity

Before running recovery commands, confirm the machine is reachable:

```bash
ssh -p <port> <user>@<host> "echo connected && pwd"
```

### Step 3: Run workspace recovery

From the monorepo root on the remote machine:

```bash
bash tools/workspace_bootstrap.sh recover \
  --instance-id <vast-instance-id> \
  --host <host> --port <port> --user <user>
```

This command:
1. Validates host prerequisites (git, mise, uv, repo layout)
2. Checks and reports blockers before proceeding
3. Syncs git submodules (if needed)
4. Re-creates missing shared directories
5. Re-syncs fungal-cv-qdrant venv if it was lost
6. Reports recovery instance tracking info
7. Runs smoke validation (directories + fungal smoke command)
8. Prints updated workspace summary with mode=recovery
9. Prints updated connection descriptor for VS Code

### Step 4: Reconnect VS Code

Use the updated connection descriptor printed by `recover` to reopen the
workspace in VS Code Remote-SSH.

### Step 5: Full re-clone (if workspace was lost)

If the previous workspace files were on ephemeral storage that was wiped:

1. Clone the monorepo fresh on the new instance
2. Run `prepare` instead of `recover` (it's a new workspace)

```bash
bash tools/workspace_bootstrap.sh prepare --non-interactive \
  --ssh-host <host> --ssh-user <user> --ssh-port <port> \
  --instance-id <vast-instance-id>
```

## Recovery Options

```bash
# Minimal recovery (just revalidate existing workspace)
bash tools/workspace_bootstrap.sh recover

# Recovery with instance tracking (for durable lookup)
bash tools/workspace_bootstrap.sh recover --instance-id <id>

# Recovery with updated connection details
bash tools/workspace_bootstrap.sh recover \
  --instance-id <id> \
  --host <new-host> --port <new-port>

# Recovery with explicit workspace root
bash tools/workspace_bootstrap.sh recover \
  --instance-id <id> \
  --workspace-root /custom/path
```

## Completion Criteria

Recovery is complete ONLY when all of these are true:
- [ ] Recovery command completed without blockers
- [ ] Smoke validation passed (status: validated)
- [ ] Connection descriptor is printed with current SSH details
- [ ] VS Code reopens the correct remote workspace root
- [ ] Instance ID is confirmed as the active recovery handle

## Rerun Safety

- `recover` is safe to rerun — submodule sync is idempotent, uv sync skips
  existing venvs, and directory creation uses `mkdir -p`
- Running `recover` after a host/port change updates the connection descriptor
  with the new values
- Running `recover` without `--instance-id` just revalidates the current
  workspace without tracking an instance

## Failure Recovery

| Symptom | Action |
|---------|--------|
| "Missing Dataset directory" | Run `prepare` first if this is actually a fresh machine |
| fungal venv is missing | The script auto-reruns `uv sync` to rebuild it |
| SSH details stale | Use `--host` and `--port` to pass refreshed values |
| Instance completely replaced | Treat as fresh setup: clone monorepo and run `prepare` |
| vastai CLI not available | Use the Vast.ai web UI to look up connection details |
