# Quickstart: Autonomous Vast.ai Setup

## Goal

Go from a local workstation with the required credentials to a validated MycoAI workspace on Vast.ai, then open that workspace in VS Code with as little manual handling as possible.

## Prerequisites

1. A Vast.ai account with an attached SSH key.
2. A local machine with SSH and VS Code plus the Remote-SSH capability.
3. Access to this MycoAI monorepo and its submodules.
4. Required external credentials available outside the repo, including any dataset-sync credentials if dataset transfer is part of the session.
5. Optional Vast.ai CLI access if you want connection metadata to be refreshed from the command line instead of the web UI.

## 1. Acquire or identify the remote machine

1. Rent or reuse a Vast.ai instance that supports SSH access.
2. Record the `instance_id` as the durable recovery handle.
3. Obtain the current SSH host, port, and user details from the platform or CLI.

## 2. Access the machine and prepare the workspace

1. Connect to the remote machine over SSH.
2. Clone or open the MycoAI monorepo on the remote machine.
3. From the monorepo root, run:

```bash
bash tools/workspace_bootstrap.sh prepare --non-interactive
```

4. Review the resulting workspace summary and retain any printed connection or recovery details.

## 3. Validate readiness

Run:

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

The workspace is ready only when the smoke-check completes successfully and no blocking prerequisite issues remain.

## 4. Open the workspace from VS Code

1. Use the surfaced SSH details or generated connection descriptor.
2. Open the remote host with VS Code Remote-SSH.
3. Open the prepared monorepo root folder on the remote machine.
4. Confirm that file browsing and an integrated terminal work.

## 5. Recover after restart, reconnect, or replacement

If the machine changes host or port, rediscover the latest SSH details from the saved `instance_id`, reconnect, and run:

```bash
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>
```

If host or port changed and is already known, include the refreshed values in the recovery call so the workflow can echo the updated connection state.

## 6. Declare setup complete

Setup is complete only when all of the following are true:

- prepare finished without blocking errors
- smoke-check passed
- the current instance details are recorded
- VS Code opened the correct remote workspace
- any remaining manual steps are documented as external platform requirements rather than unresolved setup gaps

## 7. Validation Checklist

Run through this checklist end to end before declaring setup complete.

### Prepare Phase

- [ ] `bash tools/workspace_bootstrap.sh prepare --non-interactive` completes without blocking errors
- [ ] Workspace summary shows correct `workspace_root`, `fungal_dir`, `dataset_root`, `results_root`, `weights_root`
- [ ] `rclone` availability is reported correctly
- [ ] Next steps output references `smoke-check`

### Smoke-Check Phase

- [ ] `bash tools/workspace_bootstrap.sh smoke-check` returns pass
- [ ] Shared root directories (`Dataset/`, `results/`, `weights/`) confirmed present
- [ ] Fungal-cv-qdrant smoke command succeeds

### Recovery Phase

- [ ] `bash tools/workspace_bootstrap.sh recover --instance-id <id>` completes without blocking errors
- [ ] Instance ID is logged for follow-up lookup
- [ ] Updated SSH host/port are surfaced when provided
- [ ] VS Code reopen guidance is included in output

### VS Code Connection Phase

- [ ] SSH connection descriptor is surfaced in a copyable format
- [ ] VS Code Remote-SSH can attach using the surfaced details
- [ ] Remote workspace root folder opens correctly
- [ ] Integrated terminal is functional on the remote machine

### Rerun Safety

- [ ] Running `prepare` twice does not duplicate or destroy existing workspace data
- [ ] Running `smoke-check` twice produces the same pass result
- [ ] Running `recover` twice produces consistent connection guidance

### Documentation Consistency

- [ ] Command examples in `README.md` match `tools/workspace_bootstrap.sh` usage
- [ ] `AGENTS.md` references the canonical bootstrap workflow
- [ ] `CLAUDE.md` references the canonical bootstrap workflow
- [ ] `.opencode/commands/` agent docs reference the same entrypoints
