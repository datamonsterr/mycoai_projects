# Command Contract: `.opencode/commands/*` Vast.ai setup helpers

## Purpose

Define the required behavior for agent-facing command documents that guide autonomous or low-interaction Vast.ai setup, recovery, and VS Code connection for this monorepo.

## Covered Surfaces

- A setup command that walks an agent through prerequisite checks, remote preparation, and workspace validation.
- A recovery command that re-establishes access to an existing or replaced instance.
- A VS Code connection command or section that produces editor-ready instructions from current SSH metadata.

## Required Behavior

- Commands must reference the canonical root workflow rather than inventing a parallel setup path.
- Commands must prefer executable repo entrypoints under `tools/` whenever available.
- Commands must ask for manual input only when a value cannot be derived from existing config, command output, or platform metadata.
- Commands must make rerun behavior explicit so agents can safely retry.
- Commands must surface the exact validation and recovery steps required before declaring setup complete.
- Commands must clearly separate unavoidable human actions from automatable work.

## Inputs

- Optional Vast.ai instance identifier.
- Optional refreshed SSH host or port.
- Optional workspace-root override when the default root is not being used.
- Existing local prerequisites such as SSH identity, VS Code availability, and platform credentials.

## Outputs

- A concise checklist of prerequisites and blockers.
- The exact setup or recovery commands to run.
- A connection descriptor or copyable connection instructions for VS Code Remote-SSH.
- Clear completion criteria tied to workspace validation.

## Failure Conditions

- Required prerequisites cannot be verified.
- Current connection details cannot be discovered or refreshed.
- The workspace validation command fails.
- The command documentation would require the agent to guess repository-specific paths or commands.
