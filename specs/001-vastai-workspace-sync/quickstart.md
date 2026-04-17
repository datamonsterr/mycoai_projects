# Quickstart: Vast.ai Workspace Bootstrap and Dataset Sync

## Goal

Go from a fresh Vast.ai machine to a usable MycoAI workspace with VSCode access
and a verified `Dataset/` sync path.

## Prerequisites

1. A Vast.ai account with an SSH key already attached.
2. Local VSCode with the Remote-SSH extension.
3. Access to the MycoAI repository and its submodules.
4. Google Drive credentials available outside the repo for the dataset mirror.
5. An external `rclone` config available through `RCLONE_CONFIG` or
   `~/.config/rclone/rclone.conf`.

## 1. Rent a machine

1. Choose a Vast.ai offer with SSH access and enough disk for the intended
   dataset scope.
2. Prefer direct SSH access when available for the fastest VSCode connection.
3. Record the Vast.ai `instance_id` because it is the recovery handle if host or
   port changes later.

## 2. Discover connection info

1. Use the Vast.ai UI SSH dialog or the Vast CLI to obtain current SSH host,
   port, and user details.
2. Verify terminal SSH access before trying VSCode.

## 3. Prepare the workspace

1. Clone the monorepo with submodules on the remote machine.
2. Run `mise install` from the monorepo root.
3. Run the planned bootstrap entrypoint:

   ```bash
   bash tools/workspace_bootstrap.sh prepare
   ```

4. Review the workspace summary and confirm the monorepo root plus `Dataset/`
   paths are correct.
5. Confirm `rclone` is available before trying dataset sync commands.

## 4. Connect from VSCode

1. Add the remote host to the local SSH config if needed.
2. Open the host with VSCode Remote-SSH.
3. Open the monorepo root folder on the remote machine.

## 5. Run smoke validation

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

Expected validation includes:

- shared root directories are present
- remote workspace paths are correct
- fungal-cv-qdrant dependency sync works
- the fungal-cv-qdrant smoke command runs

## 6. Validate Google Drive access with a small preview

Run a preview before any real transfer:

```bash
uv run python tools/dataset_sync.py plan --direction import --remote <drive-remote-path> --scope original/sample
```

Review the summary to confirm:

- the Drive path resolves correctly
- the local `Dataset/` target is correct
- the selected scope is small enough for proof-of-access

## 7. Import and export dataset scope

Example import:

```bash
uv run python tools/dataset_sync.py import --remote <drive-remote-path> --scope original/sample
```

Example export:

```bash
uv run python tools/dataset_sync.py export --remote <drive-remote-path> --scope segmented_image/new-batch
```

Each run should finish with a clear summary of transferred, skipped, and failed
items.

## 8. Recover after restart or replacement

1. Re-query current connection details using the stored `instance_id`.
2. Reconnect over SSH and reopen the workspace in VSCode.
3. Run:

   ```bash
   bash tools/workspace_bootstrap.sh recover
   ```

4. If the instance was replaced, re-clone the repo, rerun `prepare`, and repeat
   the dataset preview/import flow.
