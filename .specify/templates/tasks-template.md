---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Validation**: Every task list MUST include context-appropriate verification
tasks for each touched repo. Command-oriented tasks and documentation MUST use
canonical toolchains: `uv`/`uvx` for Python contexts, `pnpm` for frontend
contexts, and `gh` for workflow and PR operations. Automated tests MUST be
included whenever behavior or contracts change unless an alternative validation
task is explicitly justified. User-facing changes MUST include a manual
browser or API validation task. Product repos MAY inspect
`fungal-cv-qdrant`, but they MUST not import from it; add explicit
reimplementation tasks when translating experiment logic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Experiment repo**: `fungal-cv-qdrant/src/`,
  `fungal-cv-qdrant/src/experiments/`, `fungal-cv-qdrant/report/`
- **Backend repo**: `mycoai_retrieval_backend/src/`,
  `mycoai_retrieval_backend/tests/`
- **Frontend repo**: `mycoai_retrieval_frontend/src/` and related app config or
  validation paths
- **Shared assets**: `Dataset/`, `results/`, `weights/`,
  `species_weights.json`
- Paths shown below are examples only - adjust them to the actual repo and plan

<!-- 
  ============================================================================
  IMPORTANT: The tasks below are SAMPLE TASKS for illustration purposes only.
  
  The /speckit.tasks command MUST replace these with actual tasks based on:
  - User stories from spec.md (with their priorities P1, P2, P3...)
  - Feature requirements from plan.md
  - Entities from data-model.md
  - Endpoints from contracts/
  
  Tasks MUST be organized by user story so each story can be:
  - Implemented independently
  - Tested independently
  - Delivered as an MVP increment
  
  DO NOT keep these sample tasks in the generated tasks.md file.
  ============================================================================
-->

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize [language] project with [framework] dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

Examples of foundational tasks (adjust based on your project):

- [ ] T004 Setup database schema and migrations framework
- [ ] T005 [P] Implement authentication/authorization framework
- [ ] T006 [P] Setup API routing and middleware structure
- [ ] T007 Create base models/entities that all stories depend on
- [ ] T008 Configure error handling and logging infrastructure
- [ ] T009 Setup environment configuration management

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Validation for User Story 1 (REQUIRED) ⚠️

> **NOTE:** Include automated tests when behavior or contracts change. Use
> command, artifact, or workflow validation tasks when the work is primarily
> experiment-driven or documentation-only.

- [ ] T010 [P] [US1] Contract test for [endpoint] in [repo]/tests/contract/test_[name].py
- [ ] T011 [P] [US1] Integration test for [user journey] in [repo]/tests/integration/test_[name].py
- [ ] T012 [US1] Manual browser or API journey validation for [user journey]
- [ ] T013 [US1] Relevant workflow/check verification with `gh` or documented equivalent

### Implementation for User Story 1

- [ ] T014 [P] [US1] Create [Entity1] model in [repo]/src/models/[entity1].py
- [ ] T015 [P] [US1] Create [Entity2] model in [repo]/src/models/[entity2].py
- [ ] T016 [US1] Implement [Service] in [repo]/src/services/[service].py (depends on T014, T015)
- [ ] T017 [US1] Implement [endpoint/feature] in [repo]/src/[location]/[file].py
- [ ] T018 [US1] Add validation and error handling
- [ ] T019 [US1] Add logging for user story 1 operations

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Validation for User Story 2 (REQUIRED) ⚠️

- [ ] T020 [P] [US2] Contract test for [endpoint] in [repo]/tests/contract/test_[name].py
- [ ] T021 [P] [US2] Integration test for [user journey] in [repo]/tests/integration/test_[name].py
- [ ] T022 [US2] Manual browser or API journey validation for [user journey]
- [ ] T023 [US2] Relevant workflow/check verification with `gh` or documented equivalent

### Implementation for User Story 2

- [ ] T024 [P] [US2] Create [Entity] model in [repo]/src/models/[entity].py
- [ ] T025 [US2] Implement [Service] in [repo]/src/services/[service].py
- [ ] T026 [US2] Implement [endpoint/feature] in [repo]/src/[location]/[file].py
- [ ] T027 [US2] Integrate with User Story 1 components (if needed)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - [Title] (Priority: P3)

**Goal**: [Brief description of what this story delivers]

**Independent Test**: [How to verify this story works on its own]

### Validation for User Story 3 (REQUIRED) ⚠️

- [ ] T028 [P] [US3] Contract test for [endpoint] in [repo]/tests/contract/test_[name].py
- [ ] T029 [P] [US3] Integration test for [user journey] in [repo]/tests/integration/test_[name].py
- [ ] T030 [US3] Manual browser or API journey validation for [user journey]
- [ ] T031 [US3] Relevant workflow/check verification with `gh` or documented equivalent

### Implementation for User Story 3

- [ ] T032 [P] [US3] Create [Entity] model in [repo]/src/models/[entity].py
- [ ] T033 [US3] Implement [Service] in [repo]/src/services/[service].py
- [ ] T034 [US3] Implement [endpoint/feature] in [repo]/src/[location]/[file].py

**Checkpoint**: All user stories should now be independently functional

---

[Add more user story phases as needed, following the same pattern]

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] TXXX [P] Documentation updates in [repo]/docs/ or the relevant README
- [ ] TXXX [P] Contract or README sync across producer and consumer repos
- [ ] TXXX [P] Toolchain command sync to keep `uv`/`uvx` or `pnpm` guidance current
- [ ] TXXX [P] PR summary and validation evidence update for the final review
- [ ] TXXX Code cleanup and refactoring
- [ ] TXXX Performance optimization across all stories
- [ ] TXXX [P] Additional automated validation in the touched repo test paths
- [ ] TXXX Security hardening
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - May integrate with US1 but should be independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - May integrate with US1/US2 but should be independently testable

### Within Each User Story

- Validation tasks MUST exist for every touched repo before implementation is
  considered complete
- Automated tests MUST be added when behavior or contracts change, or the task
  list MUST explain why narrower validation is sufficient
- User-facing stories MUST include manual validation and, when browser
  automation is part of the plan, e2e coverage tasks
- Relevant workflow verification MUST be included before PR-ready completion
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All validation tasks for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all validation tasks for User Story 1 together:
Task: "Contract test for [endpoint] in [repo]/tests/contract/test_[name].py"
Task: "Integration test for [user journey] in [repo]/tests/integration/test_[name].py"

# Launch all models for User Story 1 together:
Task: "Create [Entity1] model in [repo]/src/models/[entity1].py"
Task: "Create [Entity2] model in [repo]/src/models/[entity2].py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify the planned validation matches the touched repo and risk boundary
- Keep experiment analysis and product-side reimplementation tasks separate
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
