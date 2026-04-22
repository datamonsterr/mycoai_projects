# CLI Contract: `tools/workspace_bootstrap.sh`

## Purpose

Provide the canonical root-level entrypoint that prepares, validates, and recovers a MycoAI workspace on a Vast.ai machine while surfacing connection-ready information for follow-on VS Code access.

## Entry Point

```bash
bash tools/workspace_bootstrap.sh <command> [options]
```

## Commands

### `prepare`

Prepare a freshly accessed or freshly cloned remote machine for MycoAI work.

**Required behavior**

- Validate required host prerequisites before mutating the workspace.
- Initialize the monorepo layout and shared runtime directories.
- Sync required project dependencies for the baseline research workflow.
- Print a clear workspace summary.
- Surface the next validation and connection steps, including any connection metadata that the user or agent should retain.

### `smoke-check`

Validate that the remote workspace is ready for work.

**Required behavior**

- Confirm shared root directories exist.
- Confirm required command-line tools are available.
- Confirm the canonical fungal-cv-qdrant smoke command succeeds.
- Return a clear pass/fail signal with next actions.

### `recover`

Revalidate and refresh an existing workspace after reconnect, restart, or replacement.

**Required behavior**

- Re-check workspace layout and prerequisite state.
- Accept refreshed instance or SSH details when available.
- Re-run the smoke validation subset needed after reconnect.
- Surface updated connection information and next steps for VS Code reopen.

## Contract Rules

- The script must operate on monorepo root paths.
- The script must remain idempotent and safe to rerun.
- The script must not silently overwrite or delete dataset contents.
- The script must provide outputs that support both human operators and agent-driven workflows.
- The script must separate blocking failures from informational next steps.

## Failure Conditions

- Missing repo or required submodules.
- Missing required host tools.
- Unreachable or invalid workspace root.
- Failed smoke validation.
- Missing or stale SSH details that prevent reconnect without further lookup.
