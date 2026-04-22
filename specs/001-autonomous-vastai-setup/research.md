# Phase 0 Research: Autonomous Vast.ai Setup

## Decision 1: Build on the existing root bootstrap flow instead of creating a parallel setup tool

- **Decision**: Extend `tools/workspace_bootstrap.sh` as the canonical setup, smoke-check, and recovery entrypoint rather than introducing a second Vast.ai-specific bootstrap script.
- **Rationale**: The repo already has a root-owned workspace bootstrap contract and documented prepare/smoke-check/recover flow. Improving that surface keeps rerun behavior, ownership, and validation in one place while reducing cognitive load for both humans and agents.
- **Alternatives considered**:
  - Create a new Vast.ai-only bootstrap script: rejected because it would duplicate lifecycle logic and split operator guidance.
  - Move setup into `.opencode/commands/` only: rejected because commands are guidance for agents, not the executable system of record.

## Decision 2: Treat connection metadata generation as part of setup output

- **Decision**: The improved workflow should surface SSH and editor-ready connection details as a first-class output of setup and recovery rather than leaving connection reconstruction entirely to manual lookup.
- **Rationale**: The biggest remaining friction in the current setup is the handoff from "workspace exists" to "VS Code can attach." Making connection descriptors explicit reduces manual copy/paste, supports agent-readable flows, and addresses the user's requirement for least-human-interaction setup.
- **Alternatives considered**:
  - Keep connection discovery entirely outside repo docs and tools: rejected because it preserves the current manual gap.
  - Require users to maintain custom local notes: rejected because it is brittle and not agent-friendly.

## Decision 3: Use VS Code Remote-SSH as the canonical editor path

- **Decision**: Standardize on VS Code Remote-SSH for editor access and document a direct open-the-workspace path from current SSH metadata.
- **Rationale**: The user explicitly asked for VS Code connectivity. Remote-SSH matches Vast.ai's SSH access model, avoids exposing extra services, and fits both manual developer use and agent-produced connection instructions.
- **Alternatives considered**:
  - `code-server` or browser IDEs: rejected because they add another service to install, expose, and recover.
  - VS Code tunnels: rejected because they introduce another setup path and external dependency without improving the primary SSH workflow.

## Decision 4: Separate unavoidable human approvals from automatable steps

- **Decision**: The documentation and command flows should explicitly isolate unavoidable manual steps such as marketplace rental approval, SSH key registration, or first-time extension authorization, while automating or scripting everything after those prerequisites are satisfied.
- **Rationale**: The user asked for full autonomy with as little human work as possible, but some platform boundaries cannot be eliminated. Explicitly separating these steps prevents false promises while still driving maximal automation.
- **Alternatives considered**:
  - Describe the flow as fully zero-touch: rejected because Vast.ai account actions and local editor trust prompts may still require human confirmation.
  - Leave manual steps implicit: rejected because that causes agent runs to fail late and unpredictably.

## Decision 5: Keep human and agent workflows synchronized through shared contracts

- **Decision**: Update root/operator docs and `.opencode/commands/` together, with the command docs reflecting the same primary setup, recovery, and VS Code connection path as the README guidance.
- **Rationale**: The feature is explicitly about both instructions and agent setup automation. If the human docs and agent prompts diverge, the autonomous workflow will rot quickly.
- **Alternatives considered**:
  - Update only README-style docs: rejected because agents would keep following stale setup guidance.
  - Update only `.opencode/commands/`: rejected because humans need the same canonical process and troubleshooting reference.
