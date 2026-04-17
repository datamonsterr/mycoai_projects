---

description: "Task list for Vast.ai workspace bootstrap and dataset sync"
---

# Tasks: Vast.ai Workspace Bootstrap and Dataset Sync

**Input**: Design documents from `/specs/001-vastai-workspace-sync/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Validation**: Every task list includes context-appropriate verification for the
shared monorepo root and `fungal-cv-qdrant/README.md`. Automated tests are
required for deterministic `tools/dataset_sync.py` guardrails in
`tools/tests/test_dataset_sync.py`. `tools/workspace_bootstrap.sh` is validated
with `bash -n` plus manual Vast.ai runs because its behavior depends on a real
remote host, SSH access, and external tools.

**Organization**: Tasks are grouped by user story so each story can be
implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after stated dependencies are met
- **[Story]**: Maps tasks to user stories from `spec.md` (`US1`, `US2`, `US3`)
- Every task includes an exact file path or directory path

## Path Conventions

- **Shared root tooling**: `tools/`, `tools/tests/`, `mise.toml`
- **Shared guidance**: `AGENTS.md`, `CLAUDE.md`
- **Experiment-facing onboarding**: `fungal-cv-qdrant/README.md`
- **Shared assets**: `Dataset/`, `results/`, `weights/`, `species_weights.json`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the shared monorepo entrypoints needed by all stories.

- [X] T001 Create the root tooling files `tools/workspace_bootstrap.sh`, `tools/dataset_sync.py`, and `tools/tests/test_dataset_sync.py`
- [X] T002 Add root task entrypoints for `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py` in `mise.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared command surfaces and test harness before any
user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Implement monorepo root discovery, usage output, and command dispatch in `tools/workspace_bootstrap.sh`
- [X] T004 [P] Implement monorepo root discovery, argument parsing, and `rclone` runner scaffolding in `tools/dataset_sync.py`
- [X] T005 [P] Add dataset sync fixtures, command-runner mocks, and shared assertions in `tools/tests/test_dataset_sync.py`

**Checkpoint**: Shared command surfaces exist and user story work can proceed.

---

## Phase 3: User Story 1 - Launch Remote Workspace Fast (Priority: P1) 🎯 MVP

**Goal**: Prepare a fresh Vast.ai machine, verify the monorepo workspace, and
make the VSCode Remote-SSH workflow repeatable.

**Independent Test**: Provision a fresh remote machine, run
`bash tools/workspace_bootstrap.sh prepare`, connect from VSCode Remote-SSH,
run `bash tools/workspace_bootstrap.sh smoke-check`, and confirm the monorepo
root plus `Dataset/` paths are ready.

### Implementation for User Story 1

- [X] T006 [US1] Implement the `prepare` command prerequisites, submodule bootstrap, and workspace summary in `tools/workspace_bootstrap.sh`
- [X] T007 [US1] Implement the `smoke-check` command for root path checks, required tools, and `uv --directory fungal-cv-qdrant run python -m src.prepare.init --help` in `tools/workspace_bootstrap.sh`
- [X] T008 [US1] Align `prepare` and `smoke-check` help text, exit behavior, and contract coverage with `specs/001-vastai-workspace-sync/contracts/workspace-bootstrap-cli.md` in `tools/workspace_bootstrap.sh`
- [X] T009 [P] [US1] Update fresh-instance bootstrap and VSCode Remote-SSH guidance in `fungal-cv-qdrant/README.md`
- [X] T010 [P] [US1] Update shared operator guidance for root bootstrap commands in `AGENTS.md` and `CLAUDE.md`

### Validation for User Story 1 (REQUIRED) ⚠️

> `tools/workspace_bootstrap.sh` is validated with syntax and real remote runs
> rather than unit tests because the behavior depends on a live Vast.ai host.

- [X] T011 [US1] Run `bash -n tools/workspace_bootstrap.sh` and execute the `prepare` plus `smoke-check` flow from `specs/001-vastai-workspace-sync/quickstart.md` against `tools/workspace_bootstrap.sh`

**Checkpoint**: A fresh Vast.ai machine can be turned into a VSCode-ready MycoAI
workspace and validated independently.

---

## Phase 4: User Story 2 - Sync Dataset with Google Drive (Priority: P2)

**Goal**: Provide safe preview, import, and export commands for the root
`Dataset/` directory using Google Drive.

**Independent Test**: Run `uv run python tools/dataset_sync.py plan --direction
import ...`, then perform a sample `import` and `export`, and verify the summary
output matches the selected scope without destructive deletes.

### Implementation for User Story 2

- [X] T012 [US2] Implement the `plan` command with explicit direction, scoped preview, and summary output in `tools/dataset_sync.py`
- [X] T013 [US2] Implement the `import` and `export` commands with non-destructive `rclone copy` execution in `tools/dataset_sync.py`
- [X] T014 [US2] Implement credential discovery, remote-path validation, and insufficient-disk guardrails for `Dataset/` transfers in `tools/dataset_sync.py`
- [X] T015 [US2] Align CLI arguments, defaults, and failure handling with `specs/001-vastai-workspace-sync/contracts/dataset-sync-cli.md` in `tools/dataset_sync.py`
- [X] T016 [P] [US2] Add automated coverage for direction guardrails, scope parsing, preview summaries, and `rclone` failures in `tools/tests/test_dataset_sync.py`
- [X] T017 [P] [US2] Update Google Drive remote configuration and scoped dataset sync instructions in `fungal-cv-qdrant/README.md`
- [X] T018 [P] [US2] Update shared operator guidance for dataset preview, import, and export commands in `AGENTS.md` and `CLAUDE.md`

### Validation for User Story 2 (REQUIRED) ⚠️

- [X] T019 [US2] Run `uv run --with pytest pytest tools/tests/test_dataset_sync.py` and execute the `plan`, `import`, and `export` flow from `specs/001-vastai-workspace-sync/quickstart.md` against `tools/dataset_sync.py`

**Checkpoint**: Dataset preview, import, and export work independently with safe
direction guardrails and summary output.

---

## Phase 5: User Story 3 - Recover and Resume Work (Priority: P3)

**Goal**: Recover a prepared workspace after restart, host or port changes, or
a replacement Vast.ai machine.

**Independent Test**: Re-query connection details for a restarted or replacement
machine, reconnect over SSH, run `bash tools/workspace_bootstrap.sh recover`,
and confirm the workspace returns to a validated state.

### Implementation for User Story 3

- [X] T020 [US3] Implement the `recover` command for reconnect checks, workspace revalidation, and next-step guidance in `tools/workspace_bootstrap.sh`
- [X] T021 [US3] Implement recovery handling for changed SSH host or port, missing submodules, and stale workspace state in `tools/workspace_bootstrap.sh`
- [X] T022 [P] [US3] Update restart and replacement recovery instructions in `fungal-cv-qdrant/README.md`
- [X] T023 [P] [US3] Update shared operator guidance for recovery commands in `AGENTS.md` and `CLAUDE.md`

### Validation for User Story 3 (REQUIRED) ⚠️

- [X] T024 [US3] Run `bash -n tools/workspace_bootstrap.sh` and execute the `recover` flow from `specs/001-vastai-workspace-sync/quickstart.md` against `tools/workspace_bootstrap.sh`

**Checkpoint**: A restarted or replacement Vast.ai machine can be recovered and
resumed without rebuilding operator knowledge from scratch.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency, command discoverability, and end-to-end
validation across all stories.

- [X] T025 [P] Sync final task names and descriptions for `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py` in `mise.toml`
- [X] T026 [P] Reconcile shared workflow documentation across `AGENTS.md`, `CLAUDE.md`, and `fungal-cv-qdrant/README.md`
- [X] T027 Run the full operator path from `specs/001-vastai-workspace-sync/quickstart.md` and fix any remaining workflow gaps in `tools/workspace_bootstrap.sh`, `tools/dataset_sync.py`, `fungal-cv-qdrant/README.md`, and `specs/001-vastai-workspace-sync/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Phase 1 and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2 and can proceed without User
  Story 1 once the shared scaffolding exists.
- **User Story 3 (Phase 5)**: Depends on Phase 2 and should follow User Story 1
  because it extends the same `tools/workspace_bootstrap.sh` command surface.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent after foundational work.
- **US2 (P2)**: Independent after foundational work.
- **US3 (P3)**: Depends on the `tools/workspace_bootstrap.sh` behaviors shipped
  by US1.

### Within Each User Story

- Implement the command behavior before running the story validation task.
- Keep command behavior aligned with the corresponding contract document before
  final validation.
- Update operator guidance in the same story phase as the behavior it explains.
- Complete the story-specific validation before moving to the next priority,
  except when independent stories are being staffed in parallel.

### Parallel Opportunities

- T003, T004, and T005 can run in parallel after T002.
- T009 and T010 can run in parallel after T006, T007, and T008.
- T016, T017, and T018 can run in parallel after T012, T013, T014, and T015.
- T022 and T023 can run in parallel after T020 and T021.
- T025 and T026 can run in parallel after all story phases.

---

## Parallel Example: User Story 1

```bash
# After T006-T008 complete, run the documentation updates together:
Task: "Update fresh-instance bootstrap and VSCode Remote-SSH guidance in fungal-cv-qdrant/README.md"
Task: "Update shared operator guidance for root bootstrap commands in AGENTS.md and CLAUDE.md"
```

## Parallel Example: User Story 2

```bash
# After T012-T015 complete, run test and documentation work together:
Task: "Add automated coverage in tools/tests/test_dataset_sync.py"
Task: "Update Google Drive remote configuration and scoped dataset sync instructions in fungal-cv-qdrant/README.md"
Task: "Update shared operator guidance for dataset preview, import, and export commands in AGENTS.md and CLAUDE.md"
```

## Parallel Example: User Story 3

```bash
# After T020-T021 complete, run the recovery documentation updates together:
Task: "Update restart and replacement recovery instructions in fungal-cv-qdrant/README.md"
Task: "Update shared operator guidance for recovery commands in AGENTS.md and CLAUDE.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational.
3. Complete Phase 3: User Story 1.
4. Stop and validate the fresh-instance bootstrap plus VSCode connection flow.

### Incremental Delivery

1. Deliver US1 to establish the remote workspace bootstrap.
2. Deliver US2 to add safe dataset movement against Google Drive.
3. Deliver US3 to make the workflow resilient to restart and replacement.
4. Finish with Phase 6 polish and end-to-end validation.

### Parallel Team Strategy

1. One developer completes Phases 1 and 2.
2. After foundational work, one developer can take US1 while another takes US2.
3. US3 starts after the shared workspace bootstrap behavior from US1 is stable.

---

## Notes

- All tasks follow the required checklist format: checkbox, task ID, optional
  `[P]`, required `[US#]` for story tasks, and exact file paths.
- No GitHub workflow verification task is included because the plan marks
  workflow checks as N/A unless a new workflow is added.
- The task list keeps monorepo-root tooling at `tools/` and avoids creating a
  new shared package or runtime import path.
