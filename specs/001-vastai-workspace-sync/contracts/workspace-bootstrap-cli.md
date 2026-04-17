# CLI Contract: `tools/workspace_bootstrap.sh`

## Purpose

Provide a monorepo-level operator entrypoint that prepares, validates, and
recovers a remote MycoAI workspace on a Vast.ai machine.

## Entry Point

```bash
bash tools/workspace_bootstrap.sh <command> [options]
```

## Commands

### `prepare`

Prepare a freshly accessed remote machine for MycoAI work.

**Required behavior**

- Verify the repo is available at the intended workspace path.
- Verify or install shared host prerequisites needed by the workspace flow.
- Initialize submodules and shared runtime directories expected by the monorepo.
- Run the baseline dependency bootstrap needed for the research workflow.
- Print a workspace summary that includes repo root, dataset root, and next
  validation steps.

**Inputs**

- Optional workspace root override.
- Optional non-interactive mode for repeatable remote bootstrap.

**Outputs**

- Human-readable setup summary.
- Non-zero exit when bootstrap cannot safely continue.

### `smoke-check`

Validate that the remote workspace is ready for use.

**Required behavior**

- Confirm root shared paths exist.
- Confirm required command-line tools are available.
- Confirm the canonical fungal-cv-qdrant smoke command can run.
- Report pass/fail status clearly.

**Outputs**

- Human-readable validation report.
- Non-zero exit on any failed check.

### `recover`

Revalidate an existing workspace after instance restart or reconnect.

**Required behavior**

- Re-check the expected workspace layout and shared paths.
- Re-run the smoke validation subset needed after reconnect.
- Print next actions when recovery cannot complete automatically.

## Contract Rules

- The script must operate on monorepo root paths, not submodule-relative
  stand-alone assumptions.
- The script must not require runtime imports from submodule code.
- The script must keep recovery and validation idempotent.
- The script must not silently mutate or delete `Dataset/` contents.

## Failure Conditions

- Missing repo or submodules.
- Missing required host tools.
- Missing shared root directories that cannot be created safely.
- Smoke command failure.

## Notes

- Local VSCode connection discovery remains driven by Vast.ai UI or CLI lookup;
  this contract covers the remote workspace side of the workflow.
