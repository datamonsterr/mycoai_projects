# Tasks: Autonomous Vast.ai Setup

**Input**: Design documents from `/specs/001-autonomous-vastai-setup/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Validation**: Every task list MUST include context-appropriate verification tasks for each touched repo. Command-oriented tasks and documentation MUST use canonical toolchains: `uv`/`uvx` for Python contexts, `pnpm` for frontend contexts, and `gh` for workflow and PR operations. Automated tests MUST be included whenever behavior or contracts change unless an alternative validation task is explicitly justified. User-facing changes MUST include a manual browser or API validation task. Product repos MAY inspect `fungal-cv-qdrant`, but they MUST not import from it; add explicit reimplementation tasks when translating experiment logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the existing root setup surface and documentation targets before changing behavior.

- [ ] T001 Review the current Vast.ai workflow surfaces in `tools/workspace_bootstrap.sh`, `AGENTS.md`, `CLAUDE.md`, and `.opencode/commands/`
- [ ] T002 [P] Inspect `specs/001-vastai-workspace-sync/` artifacts and reuse any still-valid setup, recovery, and connection language in `specs/001-autonomous-vastai-setup/`
- [ ] T003 [P] Identify the human-facing setup document target (`README.md` or an existing root setup guide) and record the chosen file path in `specs/001-autonomous-vastai-setup/tasks.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the shared contracts and output structure that all user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T004 Define the connection-output contract and required summary fields for `tools/workspace_bootstrap.sh` using `specs/001-autonomous-vastai-setup/contracts/workspace-bootstrap-cli.md`
- [ ] T005 [P] Define the agent command surface to add or update under `.opencode/commands/` using `specs/001-autonomous-vastai-setup/contracts/agent-vast-setup-command.md`
- [ ] T006 [P] Map prerequisite, instance-context, validation-result, and editor-descriptor fields from `specs/001-autonomous-vastai-setup/data-model.md` to concrete script and documentation outputs in `tools/workspace_bootstrap.sh` and the chosen root doc file
- [ ] T007 Create a validation checklist section in `specs/001-autonomous-vastai-setup/quickstart.md` covering prepare, smoke-check, recovery, and VS Code attach evidence

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Bootstrap a remote workspace (Priority: P1) 🎯 MVP

**Goal**: A developer or agent can run a single low-interaction setup flow that prepares the remote workspace, reports blockers early, and is safe to rerun.

**Independent Test**: Execute the documented bootstrap flow on a fresh or reset machine, rerun it once, and confirm the workspace is prepared without duplicate destructive actions.

### Validation for User Story 1 (REQUIRED) ⚠️

- [ ] T008 [US1] Run `bash -n tools/workspace_bootstrap.sh` after bootstrap-flow changes in `tools/workspace_bootstrap.sh`
- [ ] T009 [US1] Execute the first-time setup path from `specs/001-autonomous-vastai-setup/quickstart.md` and capture evidence for prepare plus smoke-check against `tools/workspace_bootstrap.sh`
- [ ] T010 [US1] Rerun the bootstrap path from `specs/001-autonomous-vastai-setup/quickstart.md` and verify rerun-safe behavior from `tools/workspace_bootstrap.sh`
- [ ] T011 [US1] Review command examples for consistency across `tools/workspace_bootstrap.sh`, the chosen root setup doc, and `.opencode/commands/`

### Implementation for User Story 1

- [ ] T012 [US1] Extend prerequisite validation, blocker messaging, and non-interactive prepare output in `tools/workspace_bootstrap.sh`
- [ ] T013 [US1] Add structured workspace summary fields and explicit next-step output for setup completion in `tools/workspace_bootstrap.sh`
- [ ] T014 [US1] Update the chosen root setup guide file with the canonical first-time Vast.ai bootstrap workflow and unavoidable manual prerequisites
- [ ] T015 [US1] Update `AGENTS.md` with the canonical autonomous bootstrap commands and completion criteria for remote setup
- [ ] T016 [US1] Update `CLAUDE.md` with the same bootstrap workflow and rerun-safe guidance used in `AGENTS.md`

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Connect from VS Code quickly (Priority: P2)

**Goal**: A prepared remote workspace can be opened from VS Code using connection-ready output instead of manual SSH reconstruction.

**Independent Test**: Use the setup-produced connection information to attach via VS Code Remote-SSH and confirm the correct folder opens and the terminal works.

### Validation for User Story 2 (REQUIRED) ⚠️

- [ ] T017 [US2] Run the VS Code attach flow from `specs/001-autonomous-vastai-setup/quickstart.md` using the current connection output from `tools/workspace_bootstrap.sh`
- [ ] T018 [US2] Manually verify file browsing and integrated terminal access in VS Code for the remote workspace described in the chosen root setup doc
- [ ] T019 [US2] Review all VS Code connection snippets for consistency across the chosen root setup doc, `AGENTS.md`, `CLAUDE.md`, and `.opencode/commands/`

### Implementation for User Story 2

- [ ] T020 [US2] Add editor-ready connection descriptor output and VS Code-specific next steps to `tools/workspace_bootstrap.sh`
- [ ] T021 [US2] Update the chosen root setup guide file with the canonical VS Code Remote-SSH workflow and copyable connection instructions
- [ ] T022 [P] [US2] Create or update `.opencode/commands/setup-vastai.md` with agent instructions for prerequisite checks, setup execution, validation, and VS Code connection
- [ ] T023 [P] [US2] Create or update `.opencode/commands/connect-vscode-vastai.md` with agent instructions for generating or using the connection descriptor from current SSH metadata

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Recover and operate autonomously (Priority: P3)

**Goal**: A developer or agent can recover access to an existing or changed Vast.ai instance, refresh workspace validity, and continue working with minimal manual steps.

**Independent Test**: Simulate a reconnect or changed host/port, run the recovery path, and confirm the workspace is revalidated and the updated connection details are ready for reuse.

### Validation for User Story 3 (REQUIRED) ⚠️

- [ ] T024 [US3] Run `bash -n tools/workspace_bootstrap.sh` after recovery-flow changes in `tools/workspace_bootstrap.sh`
- [ ] T025 [US3] Execute the recovery flow from `specs/001-autonomous-vastai-setup/quickstart.md` with `--instance-id` and capture the resulting validation and connection output from `tools/workspace_bootstrap.sh`
- [ ] T026 [US3] Execute the recovery flow with refreshed `--host` and `--port` values and verify the updated connection guidance from `tools/workspace_bootstrap.sh`
- [ ] T027 [US3] Review the recovery instructions for human/agent alignment across the chosen root setup doc, `AGENTS.md`, `CLAUDE.md`, and `.opencode/commands/`

### Implementation for User Story 3

- [ ] T028 [US3] Extend recovery messaging, refreshed instance-context handling, and post-recovery next-step output in `tools/workspace_bootstrap.sh`
- [ ] T029 [US3] Update the chosen root setup guide file with the canonical recovery workflow for reconnect, restart, and replacement scenarios
- [ ] T030 [P] [US3] Create or update `.opencode/commands/recover-vastai.md` with agent instructions for rerun-safe recovery and validation
- [ ] T031 [P] [US3] Update `.opencode/commands/setup-vastai.md` to include recovery entrypoints, blockers, and completion criteria shared with the human docs

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final synchronization, validation evidence, and handoff quality.

- [ ] T032 [P] Sync the final command names, file references, and workflow ordering across `tools/workspace_bootstrap.sh`, the chosen root setup doc, `AGENTS.md`, `CLAUDE.md`, and `.opencode/commands/`
- [ ] T033 [P] Run `uv run --with pytest pytest tools/tests/test_dataset_sync.py` to confirm adjacent root tooling still passes after the Vast.ai workflow updates
- [ ] T034 Run the full quickstart in `specs/001-autonomous-vastai-setup/quickstart.md` end to end and record setup, VS Code, and recovery evidence for PR handoff
- [ ] T035 [P] Verify whether any relevant GitHub workflow checks should be inspected with `gh` and record the result or N/A rationale in the final change summary

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - establishes the canonical prepare/smoke-check path
- **User Story 2 (P2)**: Depends on User Story 1 output because VS Code connection guidance must build on the prepared workspace summary
- **User Story 3 (P3)**: Depends on User Story 1 and should reuse the connection descriptor conventions finalized in User Story 2

### Within Each User Story

- Validation tasks MUST exist before implementation is considered complete
- Script behavior changes precede documentation synchronization
- Human docs and agent docs must be updated before the story is considered done
- Manual validation must pass before moving to the next priority

### Parallel Opportunities

- T002 and T003 can run in parallel during setup
- T005, T006, and T007 can run in parallel during the foundational phase
- T022 and T023 can run in parallel once the VS Code connection contract is implemented
- T030 and T031 can run in parallel once the recovery workflow is defined
- T032, T033, and T035 can run in parallel during polish

---

## Parallel Example: User Story 2

```bash
# Launch agent-doc updates for User Story 2 together:
Task: "Create or update .opencode/commands/setup-vastai.md with agent instructions for prerequisite checks, setup execution, validation, and VS Code connection"
Task: "Create or update .opencode/commands/connect-vscode-vastai.md with agent instructions for generating or using the connection descriptor from current SSH metadata"
```

---

## Parallel Example: User Story 3

```bash
# Launch recovery-doc updates together:
Task: "Create or update .opencode/commands/recover-vastai.md with agent instructions for rerun-safe recovery and validation"
Task: "Update .opencode/commands/setup-vastai.md to include recovery entrypoints, blockers, and completion criteria shared with the human docs"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm first-time prepare, smoke-check, and rerun-safe bootstrap behavior
5. Demo the canonical bootstrap workflow before expanding into editor and recovery improvements

### Incremental Delivery

1. Complete Setup + Foundational → shared contract ready
2. Add User Story 1 → validate bootstrap independently → deliver MVP
3. Add User Story 2 → validate VS Code connection independently → deliver
4. Add User Story 3 → validate recovery independently → deliver
5. Finish with cross-cutting sync and final evidence capture

### Parallel Team Strategy

With multiple developers:

1. One developer updates `tools/workspace_bootstrap.sh`
2. One developer updates the chosen root setup doc plus `AGENTS.md`/`CLAUDE.md`
3. One developer updates `.opencode/commands/`
4. Rejoin for manual validation and final command-sync review

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story remains independently testable through the quickstart flow
- The touched surface is root tooling and documentation only; no backend/frontend repo changes are planned
- Avoid introducing a second setup entrypoint when the existing root bootstrap flow can be extended
