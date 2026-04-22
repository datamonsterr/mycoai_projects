# Feature Specification: Autonomous Vast.ai Setup

**Feature Branch**: `[001-autonomous-vastai-setup]`  
**Created**: 2026-04-21  
**Status**: Draft  
**Input**: User description: "Help me analyze and improve current vast ai setup and write instruction, readme,  @.opencode/commands/ for agent to setup vast ai, connect it to vscode. The setup must be fully autonomous, least human interaction as possible."

## Affected Contexts *(mandatory)*

- **Primary Repo**: monorepo root tooling and documentation
- **Additional Touched Repos**: None
- **Shared Artifacts**: `tools/`, `.opencode/commands/`, root-level setup documentation, optional local workstation SSH and editor configuration guidance
- **Execution Tooling**: `bash`, `uv`/`uvx`, `gh`, `mise`, OpenSSH, VS Code Remote SSH
- **Experiment Dependency**: N/A
- **Reimplementation Boundary**: N/A

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bootstrap a remote workspace (Priority: P1)

A developer can start from a fresh local workstation, run a single documented setup path, and get a ready-to-use Vast.ai workspace that mirrors the project expectations with minimal manual decisions.

**Why this priority**: Without a repeatable bootstrap path, every later step is error-prone and expensive.

**Independent Test**: Can be fully tested by following the documented bootstrap flow on a clean machine and confirming the remote workspace is provisioned, project files are available, and prerequisite checks pass.

**Acceptance Scenarios**:

1. **Given** a developer has the required local credentials and tools, **When** they execute the primary setup flow, **Then** a Vast.ai instance is provisioned or selected, the workspace is prepared, and the setup reports clear next steps or completion.
2. **Given** the workspace setup is interrupted, **When** the developer reruns the same flow, **Then** the process resumes safely without duplicating critical resources or requiring the developer to restart manually.

---

### User Story 2 - Connect from VS Code quickly (Priority: P2)

A developer can open the prepared Vast.ai workspace in VS Code with a documented low-friction path that avoids manual SSH troubleshooting.

**Why this priority**: The main value of the remote workspace is lost if developers cannot reliably attach their editor.

**Independent Test**: Can be fully tested by using the documented connection flow to attach VS Code to the prepared remote workspace and confirming files are editable and terminal access works.

**Acceptance Scenarios**:

1. **Given** a prepared remote workspace and local VS Code installation, **When** the developer follows the documented connection flow, **Then** VS Code opens the correct remote directory without requiring them to handcraft connection details.
2. **Given** the remote host details change between sessions, **When** the developer reruns the connection helper, **Then** the updated connection information is surfaced in a format VS Code can use immediately.

---

### User Story 3 - Recover and operate autonomously (Priority: P3)

A developer or agent can recover an existing Vast.ai workspace, verify health, and reuse it through agent-readable commands and documentation instead of bespoke manual shell work.

**Why this priority**: Remote instances are ephemeral, so recovery and repeatability are essential for day-to-day use and agent autonomy.

**Independent Test**: Can be fully tested by simulating a reconnect or recovery scenario and confirming the command flow restores access, validates the workspace, and documents any manual action that remains.

**Acceptance Scenarios**:

1. **Given** an existing instance identifier or saved connection context, **When** the recovery flow is executed, **Then** the workspace is rediscovered, synchronized, and validated for continued work.
2. **Given** required prerequisites are missing or invalid, **When** a developer runs the setup or recovery flow, **Then** the system halts early with actionable remediation steps instead of failing mid-process.

---

### Edge Cases

- What happens when the Vast.ai instance is already running but the local connection metadata is stale?
- How does the system handle missing SSH keys, missing editor prerequisites, or missing remote-storage credentials before provisioning begins?
- What happens when the workspace bootstrap partially completes and is rerun by a human or agent?
- How does the system handle an instance that was destroyed and recreated with a new host, port, or identifier?
- What happens when VS Code is installed but the remote-connection capability is not yet available locally?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a single primary setup path that guides a developer or agent from local prerequisite validation through remote workspace readiness.
- **FR-002**: System MUST document all prerequisites, credentials, and local tooling needed before setup begins.
- **FR-003**: System MUST minimize manual data entry by reusing stored configuration, derived values, or discoverable instance metadata whenever available.
- **FR-004**: System MUST support both first-time setup and rerun-safe recovery of an existing Vast.ai workspace.
- **FR-005**: System MUST provide clear success and failure signals for each major phase: prerequisite validation, instance access, workspace preparation, dataset availability, and editor connection.
- **FR-006**: System MUST expose agent-usable command documentation under `.opencode/commands/` for setup, recovery, and connection workflows.
- **FR-007**: System MUST provide a human-readable README or equivalent instruction document that explains the recommended workflow, expected inputs, outputs, and troubleshooting steps.
- **FR-008**: System MUST produce or surface connection details in a format that can be used directly for VS Code remote access.
- **FR-009**: System MUST include a verification step that confirms the prepared workspace is usable for project work after setup or recovery.
- **FR-010**: System MUST describe which remaining manual steps cannot be automated and how to complete them with the fewest possible user actions.
- **FR-011**: System MUST preserve safe behavior on rerun by avoiding duplicate workspace initialization, duplicate configuration writes, or destructive overwrites unless explicitly requested.
- **FR-012**: System MUST support non-interactive or low-interaction execution suitable for agent-driven operation.

### Key Entities *(include if feature involves data)*

- **Workspace Setup Profile**: The documented or persisted inputs required to prepare a Vast.ai development environment, including prerequisites, identity, storage location, and preferred connection method.
- **Remote Instance Context**: The discovered or supplied details needed to access a specific Vast.ai machine, including identifiers, host information, SSH access details, and lifecycle state.
- **Workspace Validation Result**: The structured outcome of setup, recovery, and smoke-check steps, including pass/fail state, missing prerequisites, and next actions.
- **Editor Connection Descriptor**: The connection-ready data a developer or agent uses to open the remote workspace in VS Code without reconstructing SSH details manually.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can complete the documented end-to-end setup from prerequisites to remote workspace readiness in 20 minutes or less, excluding external instance allocation time.
- **SC-002**: At least 90% of reruns of the setup or recovery flow complete without requiring manual edits to previously generated configuration.
- **SC-003**: A user can open the prepared remote workspace in VS Code within 3 minutes after setup completes.
- **SC-004**: 100% of documented setup paths include a clear validation step that confirms whether the workspace is ready for development.
- **SC-005**: All remaining manual actions are reduced to credential provision, one-time editor authorization, or other unavoidable external approvals and are explicitly documented.

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: Specified setup, smoke-check, recovery, and documentation validation commands pass in the monorepo root; command examples are present and internally consistent.
- **Workflow Checks**: Relevant repository automation or CI validation is identified if available; otherwise N/A with rationale.
- **Manual Validation**: A full workstation-to-Vast.ai-to-VS Code journey is exercised and recorded, including first-time setup and reconnect/recovery.
- **PR Evidence**: PR includes updated setup instructions, agent command docs, validation outputs, remaining manual steps, and any screenshots or copied connection output needed to prove the VS Code flow.

## Assumptions

- Developers already possess valid Vast.ai, SSH, and any remote-storage credentials needed to access external services.
- The feature may improve existing scripts and docs rather than replacing the entire remote-workspace approach.
- A local machine can install required command-line tools and VS Code extensions before setup begins.
- The preferred v1 outcome is least-human-interaction automation, not zero-click automation in cases blocked by third-party authentication or marketplace approvals.
