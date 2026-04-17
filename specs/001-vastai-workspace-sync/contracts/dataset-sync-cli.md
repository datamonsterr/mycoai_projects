# CLI Contract: `tools/dataset_sync.py`

## Purpose

Provide a safe monorepo-level CLI for previewing and executing Google Drive
imports and exports for the root `Dataset/` directory.

## Entry Point

```bash
uv run python tools/dataset_sync.py <command> [options]
```

## Commands

### `plan`

Preview a proposed transfer without changing files.

**Required inputs**

- `--direction import|export`
- `--remote <drive-remote-path>`

**Optional inputs**

- `--dataset-root <path>` defaulting to the monorepo root `Dataset/`
- `--scope <path>` repeatable for folder-scoped transfer
- `--include <pattern>` repeatable for pattern filtering

**Required behavior**

- Validate local and remote targets.
- Confirm the transfer direction clearly.
- Show a proof-of-access preview for the requested scope.
- Emit a summary of what would transfer, skip, or fail.

### `import`

Copy selected content from Google Drive into local `Dataset/`.

**Required behavior**

- Use non-destructive copy semantics.
- Require explicit direction confirmation in output before transfer begins.
- Support the same scope controls as `plan`.
- Emit a final summary of transferred, skipped, and failed items.

### `export`

Copy selected content from local `Dataset/` to Google Drive.

**Required behavior**

- Use non-destructive copy semantics.
- Require explicit direction confirmation in output before transfer begins.
- Support the same scope controls as `plan`.
- Emit a final summary of transferred, skipped, and failed items.

## Contract Rules

- `Dataset/` is the default and canonical local root.
- Direction must be explicit for every real transfer.
- The initial implementation must not expose destructive mirror behavior as the
  default workflow.
- Credentials must be resolved from an external secret/config source, not from
  files committed to the repo.
- Each command must produce human-readable output suitable for operator review.

## Failure Conditions

- Missing or invalid Drive credentials.
- Unreachable remote path.
- Missing or invalid local dataset root.
- Insufficient free disk for the requested import.
- Transfer interruption or partial failure.

## Notes

- The implementation is expected to delegate transport to `rclone` while keeping
  local path validation, direction guardrails, and summaries inside the CLI.
