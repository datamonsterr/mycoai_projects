# Feature Specification: Vast.ai Workspace Bootstrap and Dataset Sync

**Feature Branch**: `001-vastai-workspace-sync`  
**Created**: 2026-04-16  
**Status**: Draft  
**Input**: User description: "I want to setup this project so I can have a setup in vast ai as fast as possible connect with vscode, has tools/ to sync Dataset into google drive"

## Affected Contexts *(mandatory)*

- **Primary Repo**: shared monorepo root (`tools/`, setup docs, and workspace entrypoints)
- **Additional Touched Repos**: `fungal-cv-qdrant`
- **Shared Artifacts**: `Dataset/`
- **Execution Tooling**: `uv`/`uvx` for project utilities and documented shell steps for monorepo-level remote workspace bootstrap
- **Experiment Dependency**: None
- **Reimplementation Boundary**: N/A

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch Remote Workspace Fast (Priority: P1)

As a researcher, I want a repeatable remote workspace setup for a rented Vast.ai
machine so I can open the project in VSCode quickly and start working without
manual environment reconstruction.

**Why this priority**: Without a fast and repeatable remote workspace, every
new machine setup delays research work and increases the chance of environment
drift.

**Independent Test**: Provision a fresh remote machine, follow the documented
bootstrap flow, connect from VSCode, and confirm the project is ready for use.

**Acceptance Scenarios**:

1. **Given** a freshly rented remote machine and access to the project,
   **When** the researcher follows the bootstrap workflow, **Then** the
   workspace is prepared with the project files and shared data paths in their
   expected locations.
2. **Given** a prepared remote workspace, **When** the researcher connects from
   VSCode, **Then** they can open and edit the project without manually hunting
   for connection details or startup steps.
3. **Given** a prepared remote workspace, **When** the researcher performs the
   documented smoke check, **Then** they can confirm the environment is usable
   before starting longer-running work.

---

### User Story 2 - Sync Dataset with Google Drive (Priority: P2)

As a researcher, I want a repeatable way to move `Dataset/` between the remote
workspace and Google Drive so I can avoid slow ad hoc copying and keep the
dataset available across rented machines.

**Why this priority**: Dataset movement is a recurring bottleneck for remote GPU
work, and reliable sync is required to make the remote workspace practical.

**Independent Test**: Use the provided sync workflow to import a sample dataset
from Google Drive into `Dataset/`, then export a controlled change back to the
Drive mirror.

**Acceptance Scenarios**:

1. **Given** a remote workspace with access to a Google Drive dataset mirror,
   **When** the researcher runs the dataset import workflow, **Then** the
   selected content is copied into `Dataset/` and the outcome is clearly
   reported.
2. **Given** local dataset changes in the workspace, **When** the researcher
   runs the dataset export workflow, **Then** the selected updates are pushed to
   the Google Drive mirror and the outcome is clearly reported.
3. **Given** a large dataset, **When** the researcher wants to validate access
   before a full transfer, **Then** they can perform a smaller proof-of-access
   sync first.

---

### User Story 3 - Recover and Resume Work (Priority: P3)

As a researcher, I want restart and recovery guidance for the remote workspace
so I can reconnect after an instance restart, address change, or replacement
without rebuilding everything from scratch.

**Why this priority**: Remote GPU instances are temporary by nature, so recovery
steps are necessary to keep the setup practical over time.

**Independent Test**: Simulate a reconnect or restart case and confirm the user
can regain VSCode access, revalidate the workspace, and continue using the
dataset sync workflow.

**Acceptance Scenarios**:

1. **Given** a previously prepared remote workspace, **When** the machine is
   restarted or its connection details change, **Then** the researcher can use
   the recovery guidance to reconnect and continue working.
2. **Given** a replacement remote machine, **When** the researcher repeats the
   documented setup, **Then** they can restore a working environment and regain
   access to the dataset mirror without relying on undocumented tribal knowledge.

### Edge Cases

- What happens when the remote machine does not have enough free storage for the
  selected dataset sync?
- How does the workflow handle expired Google Drive access, missing permissions,
  or a disconnected remote session during transfer?
- What happens when `Dataset/` already contains files that differ from the Drive
  mirror?
- How does the user validate the workspace if VSCode remote access succeeds but
  the project still lacks required data paths or startup readiness?
- What happens when the researcher only wants to sync one subfolder or a small
  sample before committing to a full transfer?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide a single bootstrap workflow for taking a
  freshly rented Vast.ai machine from first access to a ready-to-use project
  workspace.
- **FR-002**: The bootstrap workflow MUST include clear steps for connecting to
  the remote workspace from VSCode.
- **FR-003**: The prepared workspace MUST expose the project files and required
  shared data paths in locations that match the monorepo conventions already
  used by the project.
- **FR-004**: The shared workspace bootstrap and dataset sync utilities MUST be
  available from the monorepo `tools/` area so they can operate on root-level
  paths without requiring users to start from a specific submodule.
- **FR-005**: The setup guidance MUST clearly separate one-time prerequisites
  from per-machine bootstrap steps.
- **FR-006**: The project MUST provide a repeatable workflow for syncing
  `Dataset/` between the remote workspace and a Google Drive mirror.
- **FR-007**: The dataset sync workflow MUST support both importing data into
  the remote workspace and exporting selected updates back to Google Drive.
- **FR-008**: The dataset sync workflow MUST allow the user to validate access
  with a smaller sample or scoped transfer before running a full dataset sync.
- **FR-009**: The dataset sync workflow MUST clearly report what was
  transferred, skipped, or failed so the user can trust the final dataset
  state.
- **FR-010**: The dataset sync workflow MUST protect the user from accidental
  destructive changes by making the transfer direction and target explicit
  before data movement begins.
- **FR-011**: The setup package MUST include a smoke-validation path that proves
  the user can open the project, access `Dataset/`, and run at least one
  project command after setup.
- **FR-012**: The setup guidance MUST include restart and recovery steps for
  reconnecting after a remote instance restart, address change, or replacement.
- **FR-013**: When setup or sync cannot complete because of missing storage,
  network access, or credentials, the workflow MUST stop with clear next steps
  instead of leaving the user with an ambiguous partial setup.

### Key Entities *(include if feature involves data)*

- **Workspace Profile**: The remote working environment for this project,
  including connection context, readiness status, and expected project/data
  locations.
- **Dataset Sync Session**: A single transfer attempt between the remote
  workspace and Google Drive, including direction, scope, status, and outcome
  summary.
- **Dataset Mirror**: The expected relationship between the workspace copy of
  `Dataset/` and its Google Drive counterpart.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A first-time user can go from a freshly rented remote machine to
  an editable project workspace connected through VSCode in 20 minutes or less
  by following the provided setup flow.
- **SC-002**: At least 90% of trial setup runs on fresh remote machines complete
  without requiring undocumented troubleshooting steps.
- **SC-003**: Users can validate dataset access with a small sample sync in 5
  minutes or less before starting a full transfer.
- **SC-004**: A completed dataset sync results in no missing files relative to
  the user-selected source scope, and the user receives a clear transfer
  summary.
- **SC-005**: After a routine machine restart or address change, a user can
  reconnect and resume work in 10 minutes or less using the provided recovery
  guidance.

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: Verify the documented monorepo `tools/` bootstrap on a
  clean remote machine; confirm VSCode remote editing works; validate a sample
  dataset import and export flow for `Dataset/`; run `uv --directory
  fungal-cv-qdrant sync`; run `uv --directory fungal-cv-qdrant run python -m
  src.prepare.init --help` from the connected workspace.
- **Workflow Checks**: N/A unless a new CI or workflow check is added for the
  remote setup or dataset sync flow.
- **Manual Validation**: Provision a fresh Vast.ai machine, complete the setup,
  connect from VSCode, sync a sample folder between Google Drive and `Dataset/`,
  and complete the smoke validation path.
- **PR Evidence**: Include the remote setup instructions, proof of VSCode
  connection, a dataset sync transcript or summary, smoke-check output, and any
  prerequisite caveats or recovery notes.

## Assumptions

- The target user has a valid Vast.ai account, remote connection access, and
  permission to use a Google Drive dataset mirror.
- The first release is optimized for a single researcher or developer workflow,
  not a shared multi-user environment.
- This feature covers workspace bootstrap, VSCode connection, and `Dataset/`
  transfer only; broader job orchestration and production deployment remain out
  of scope.
- Shared setup and sync entrypoints will live at the monorepo root because they
  operate on root-level workspace paths.
- The rented remote machine has enough outbound network access and attached
  storage to hold the dataset scope selected by the user.
