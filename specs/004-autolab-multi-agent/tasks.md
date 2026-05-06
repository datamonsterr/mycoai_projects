# Tasks: Autolab Multi-Agent System for fungal-cv-qdrant

**Input**: Design documents from `/specs/004-autolab-multi-agent/`
**Branch**: `004-autolab-multi-agent`
**Prerequisites**: plan.md ✓ spec.md ✓ research.md ✓ data-model.md ✓ contracts/ ✓ quickstart.md ✓

**Validation**: Every task includes verification in each touched repo using canonical toolchains (`uv`/`uvx` for Python, `gh` for GitHub). Testing plan included per user request: pytest for experiment packages, `opencode run "test"` smoke test for agent/tool configuration, concurrent Worker isolation test.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Multi-Repo Branching & Infrastructure)

**Purpose**: Feature branch creation in affected repos, runtime directories, gitignore updates.

- [x] T001 [P] Create feature branch in fungal-cv-qdrant submodule: `git submodule update --init repos/fungal-cv-qdrant && git -C repos/fungal-cv-qdrant checkout -b 004-autolab-multi-agent`
- [x] T002 [P] Create runtime directories: `mkdir -p repos/fungal-cv-qdrant/.runtime/worktrees repos/fungal-cv-qdrant/research/papers`
- [x] T003 Add `.runtime/worktrees/` to `repos/fungal-cv-qdrant/.gitignore`
- [x] T004 [P] Create stub research notebook files: `repos/fungal-cv-qdrant/research/paper-ideas.md`, `repos/fungal-cv-qdrant/research/results.tsv`, `repos/fungal-cv-qdrant/research/do-not-repeat.md`
- [x] T005 [P] Verify `.opencode/agents/autolab.md`, `researcher.md`, `planner.md`, `worker.md`, `reporter.md` exist (created in planning phase — confirm presence)
- [x] T006 [P] Verify `.opencode/tools/hypothesis-validator.ts` and `experiment-test-runner.ts` exist (created in planning phase — confirm presence)
- [x] T007 [P] Verify `.opencode/plugins/autolab-compaction.ts` exists (created in planning phase — confirm presence)
- [x] T008 Install plugin dependencies: confirm `.opencode/package.json` lists `@opencode-ai/plugin` and run install if needed
- [ ] T009 **[TEST]** Run `opencode run "list available agents"` and verify `autolab`, `researcher`, `planner`, `worker`, `reporter` appear in output — smoke test agent registration
- [ ] T010 **[TEST]** Run `opencode run "use hypothesis-validator tool to check strategy: test-baseline for experiment: retrieval"` and verify tool returns VALID or DUPLICATE (not a crash)

---

## Phase 2: Foundational (Blocking Prerequisites — Experiment Package Contract)

**Purpose**: Restructure `retrieval` and `threshold` packages to expose the uniform `run(params) -> ExperimentResult` contract. All Worker and Planner tasks depend on this. Must complete before user story phases.

**⚠️ CRITICAL**: No worker can run experiments safely until this phase is complete.

### Validation for Foundational Phase ⚠️

- [x] T011 [P] Verify restructured `retrieval` package imports without side effects: `uv --directory repos/fungal-cv-qdrant run python -c "import src.experiments.retrieval.run; print('ok')"`
- [x] T012 [P] Verify restructured `threshold` package imports without side effects: `uv --directory repos/fungal-cv-qdrant run python -c "import src.experiments.threshold.run; print('ok')"`
- [x] T013 [P] Run ruff on restructured packages: `uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/retrieval/ src/experiments/threshold/`
- [x] T014 [P] Run mypy on restructured packages: `uv --directory repos/fungal-cv-qdrant run mypy src/experiments/retrieval/ src/experiments/threshold/ --ignore-missing-imports`
- [x] T015 Write pytest tests for `ExperimentResult` dataclass and `run()` interface in `repos/fungal-cv-qdrant/tests/test_experiment_contract.py`
- [x] T016 Run pytest contract tests: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_experiment_contract.py -v`
- [ ] T017 **[TEST]** Run `opencode run "use experiment-test-runner tool on experiments: ['retrieval', 'threshold'] with checks: ['ruff','mypy','import']"` — verify tool reports pass
- [ ] T018 Baseline F1 comparison: run original `retrieval` and `threshold` via `prepare.py`, record baseline F1 scores for regression check (SC-004)

### Implementation for Foundational Phase

- [x] T019 [P] Create `ExperimentParams` and `ExperimentResult` dataclasses in `repos/fungal-cv-qdrant/src/experiments/retrieval/run.py` with fields: `run_id`, `output_root`, `description` (params); `f1_score`, `strategy_name`, `artifact_paths`, `run_id` (result)
- [x] T020 [P] Wrap existing `retrieval` experiment logic inside `run(params: ExperimentParams) -> ExperimentResult` in `repos/fungal-cv-qdrant/src/experiments/retrieval/run.py` — scope all writes to `params.output_root`
- [x] T021 Create `repos/fungal-cv-qdrant/src/experiments/retrieval/cli.py` with `argparse` wrapping `run()` for `uv run python -m src.experiments.retrieval.cli` invocation
- [x] T022 [P] Create `ExperimentParams` and `ExperimentResult` dataclasses in `repos/fungal-cv-qdrant/src/experiments/threshold/run.py`
- [x] T023 [P] Wrap existing `threshold` logic inside `run(params: ExperimentParams) -> ExperimentResult` in `repos/fungal-cv-qdrant/src/experiments/threshold/run.py`
- [x] T024 Create `repos/fungal-cv-qdrant/src/experiments/threshold/cli.py` with argparse wrapper
- [x] T025 Write `results/<run_id>/results.json` output in both `retrieval/run.py` and `threshold/run.py` per experiment-run-contract.md schema
- [ ] T026 Verify F1 scores from restructured packages match baseline (SC-004): run restructured `retrieval` with same params, compare F1

**Checkpoint**: `retrieval` and `threshold` packages restructured, F1 regression clean, contract tests pass.

---

## Phase 3: User Story 6 — Experiment Package Contract (Priority: P1) 🎯

**Goal**: All 9 experiment packages expose uniform `run()` contract (priority 1 = `retrieval` + `threshold` done in Phase 2; this phase covers the 7 remaining packages in a second pass).

**Independent Test**: Run any remaining experiment via `cli.py` with a unique `run_id`, verify output lands under `results/<run_id>/` and not in global paths.

**Note**: User Story 6 is P1 alongside US1 and US3 — all three are blocking for safe parallel Worker execution.

### Validation for US6

- [x] T027 [P] [US6] Run ruff on all 7 remaining packages: `uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/cross_validation/ src/experiments/feature_extraction/ src/experiments/finetune_dl/ src/experiments/kmeans_segmentation/ src/experiments/yolo_cross_validation/ src/experiments/yolo_dataset/ src/experiments/yolo_segmentation/`
- [x] T028 [P] [US6] Run `uv --directory repos/fungal-cv-qdrant run pytest tests/test_experiment_contract.py -v` against all 9 packages after restructure
- [x] T029 [US6] Concurrent isolation smoke test: invoke two `cli.py` runs of `retrieval` with different `run_id` values simultaneously, confirm non-overlapping output under `results/`

### Implementation for US6

- [x] T030 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/cross_validation/` — add `run.py` + `cli.py`
- [x] T031 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/feature_extraction/` — add `run.py` + `cli.py`
- [x] T032 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/finetune_dl/` — add `run.py` + `cli.py`
- [x] T033 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/kmeans_segmentation/` — add `run.py` + `cli.py`
- [x] T034 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/yolo_cross_validation/` — add `run.py` + `cli.py`
- [x] T035 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/yolo_dataset/` — add `run.py` + `cli.py`
- [x] T036 [P] [US6] Restructure `repos/fungal-cv-qdrant/src/experiments/yolo_segmentation/` — add `run.py` + `cli.py`
- [x] T037 [US6] Update `repos/fungal-cv-qdrant/tests/test_experiment_contract.py` to cover all 9 packages

**Checkpoint**: All 9 packages expose `run()` + `cli.py`. Concurrent runs produce isolated output.

---

## Phase 4: User Story 3 — Worker Agent (Priority: P1)

**Goal**: Worker agent creates an isolated git worktree, modifies `run_accuracy.py`, runs `prepare.py`, appends result to shared CSV with file lock, and exits cleanly.

**Independent Test**: Manually invoke `@worker` agent with a hypothesis assignment block; verify worktree created at `.runtime/worktrees/<experiment-id>/`, `prepare.py` completes, one row appended to `results/autoresearch/retrieval.csv`, worktree cleaned up.

### Validation for US3

- [x] T038 [US3] Write pytest test `repos/fungal-cv-qdrant/tests/test_worker_isolation.py`: invoke two Worker-style runs with different `run_id` on `retrieval`, assert output directories non-overlapping and shared CSV has 2 rows appended correctly
- [x] T039 [US3] Run worker isolation test: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_worker_isolation.py -v`
- [ ] T040 [US3] Manual Worker invocation: invoke `@worker` agent with a prepared hypothesis block for `retrieval` experiment; verify worktree created, `prepare.py` runs, CSV appended, worktree removed
- [ ] T041 [US3] Failure case test: invoke `@worker` with a broken `run_accuracy.py` (intentional syntax error); verify worker logs failure gracefully and does not corrupt CSV or other worktrees
- [ ] T042 [US3] **[TEST]** Run `opencode run "invoke worker agent with hypothesis: experiment=retrieval, run_id=test-worker-001, branch=autoresearch/retrieval/1-test, description=test run"` — verify agent completes without crash

### Implementation for US3

- [x] T043 [US3] Write `repos/fungal-cv-qdrant/src/autolab/csv_append.py` — lock-safe CSV append utility using `fcntl.flock` (extracted from Worker agent instructions into importable module)
- [x] T044 [US3] Write `repos/fungal-cv-qdrant/tests/test_csv_append.py` — unit test concurrent CSV writes from 2 threads, verify no data corruption
- [x] T045 [US3] Run CSV append unit tests: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_csv_append.py -v`
- [x] T046 [US3] Verify `repos/fungal-cv-qdrant/.runtime/worktrees/` is in `.gitignore` and tracked worktree list is clean
- [x] T047 [US3] Validate `worker.md` agent frontmatter — confirm bash permissions cover all required git worktree + uv run commands and nothing extra

**Checkpoint**: Worker creates isolated worktree, runs experiment, appends to CSV atomically, cleans up. Two concurrent Workers do not corrupt each other.

---

## Phase 5: User Story 1 — End-to-End Autolab Loop (Priority: P1) 🎯 MVP

**Goal**: Scientist prompts `autolab` agent with one line; full Researcher → Planner → Worker → Reporter loop completes; staircase chart updated; summary returned.

**Independent Test**: Launch `opencode` in monorepo root, invoke `@autolab` with "run one autoresearch pass on retrieval experiment", verify: Planner queues ≥1 hypothesis, Worker creates worktree, `prepare.py` runs, Reporter summary produced with staircase chart path.

### Validation for US1

- [ ] T048 [US1] **[TEST]** Run `opencode run "ask autolab to run one autoresearch pass on the retrieval experiment"` — verify output includes a staircase chart path and an F1 score
- [ ] T049 [US1] Verify staircase chart updated at `results/autoresearch/retrieval.png` after loop: check file modification timestamp newer than before run
- [ ] T050 [US1] Verify `repos/fungal-cv-qdrant/research/results.tsv` has ≥1 new row after loop
- [ ] T051 [US1] Multiple-worker loop test: prompt `@autolab` with 2 hypotheses; verify 2 Workers run, 2 rows appended, no corruption
- [x] T052 [US1] Verify `autolab.md` task permission topology is correct: `@researcher`, `@planner`, `@worker`, `@reporter` all invocable from `autolab`
- [ ] T053 [US1] **[TEST]** `opencode run "test"` — confirm opencode can invoke a named command `test`; if no `test` command registered, register one in `.opencode/commands/` that runs `uv --directory repos/fungal-cv-qdrant run pytest tests/ -q` and rerun

### Implementation for US1

- [x] T054 [US1] Register `test` command in `.opencode/commands/test.md` that runs: `uv --directory repos/fungal-cv-qdrant run pytest tests/ -q && uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/`
- [ ] T055 [US1] **[TEST]** Run `opencode run "test"` after T054 — confirm command executes pytest + ruff and returns pass/fail
- [x] T056 [US1] Verify `autolab.md` frontmatter: `mode: primary`, `model: 9router/BigBrain`, `steps: 60`, task permission allows all 4 subagents
- [x] T057 [US1] Verify delegation chain works end-to-end: `autolab → planner → [worker × N] → reporter` with no agent attempting to edit experiment code directly
- [x] T058 [US1] Update `AGENTS.md` with Autolab agent system description, model tiers, and invocation instructions

**Checkpoint**: One-line Autolab prompt triggers full loop. `opencode run "test"` passes. Staircase chart and TSV updated.

---

## Phase 6: User Story 2 — Researcher Agent (Priority: P2)

**Goal**: `@researcher` searches web, downloads PDF, converts via markitdown, extracts methodology, validates fit, writes structured entry to `research/paper-ideas.md`.

**Independent Test**: Invoke `@researcher` with topic "fungal species retrieval using feature embeddings"; verify `research/papers/<slug>.md` created, one structured entry added to `research/paper-ideas.md` with all required fields.

### Validation for US2

- [x] T059 [P] [US2] Verify `research/paper-ideas.md` entry format: parse output with regex for required fields (URL, Status, Methodology, Fit Assessment, Proposed Strategy)
- [ ] T060 [US2] **[TEST]** Run `opencode run "ask researcher agent to find one paper about fungal retrieval feature embeddings"` — verify `research/papers/` gains ≥1 file and `paper-ideas.md` gains ≥1 entry
- [x] T061 [US2] Verify markitdown MCP is available: `uvx --from markitdown-mcp markitdown-mcp --version` (or check MCP config)
- [ ] T062 [US2] Duplicate prevention test: run `@researcher` twice with same topic; verify no duplicate entries added to `paper-ideas.md`

### Implementation for US2

- [x] T063 [US2] Verify `researcher.md` frontmatter: `model: 9router/BigBrain`, `webfetch: allow`, `websearch: allow`, edit permission scoped to `repos/fungal-cv-qdrant/research/**` only
- [x] T064 [US2] Create template stub `repos/fungal-cv-qdrant/research/paper-ideas.md` with header and format instructions so Researcher knows expected format
- [x] T065 [US2] Create template stub `repos/fungal-cv-qdrant/research/do-not-repeat.md` with header
- [x] T066 [US2] Write pytest test `repos/fungal-cv-qdrant/tests/test_research_notebook.py` — validate `paper-ideas.md` entry parser (check required fields present)
- [x] T067 [US2] Run research notebook test: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_research_notebook.py -v`

**Checkpoint**: Researcher produces valid, parseable `paper-ideas.md` entries. Planner can read them without modification.

---

## Phase 7: User Story 4 — Planner Agent (Priority: P2)

**Goal**: Planner reads `paper-ideas.md`, deduplicates, assigns `run_id` + branch, updates `results.tsv`, returns worker assignments.

**Independent Test**: Populate `paper-ideas.md` with 2 `pending` entries; invoke `@planner`; verify exactly 2 worker assignments returned, both entries marked `in-progress`, 2 placeholder rows in `results.tsv`.

### Validation for US4

- [x] T068 [US4] Write pytest test `repos/fungal-cv-qdrant/tests/test_planner_queue.py` — create mock `paper-ideas.md` with 1 pending + 1 in-progress entry; verify planner logic assigns only the pending one
- [x] T069 [US4] Run planner queue test: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_planner_queue.py -v`
- [ ] T070 [US4] **[TEST]** Run `opencode run "ask planner agent to queue hypotheses from research/paper-ideas.md"` — verify TSV updated and assignment block returned
- [ ] T071 [US4] Duplicate prevention test: invoke `@planner` twice on same `paper-ideas.md`; verify second invocation skips already-in-progress entries

### Implementation for US4

- [x] T072 [US4] Verify `planner.md` frontmatter: `model: 9router/MidBrain`, edit permission scoped to `research/results.tsv` + `research/do-not-repeat.md` only
- [x] T073 [US4] Create `repos/fungal-cv-qdrant/research/results.tsv` with header row: `timestamp\texperiment\trun_id\tstrategy\tf1_score\tis_new_best\tworker_branch`
- [ ] T074 [US4] Verify `hypothesis-validator` tool correctly detects duplicates: run `opencode run "use hypothesis-validator tool for strategy: cosine-top5 on experiment: retrieval"` before and after adding that strategy to `paper-ideas.md`

**Checkpoint**: Planner assigns work without duplication. TSV updated. Worker assignments are parseable.

---

## Phase 8: User Story 5 — Reporter Agent (Priority: P3)

**Goal**: Reporter reads staircase CSV + TSV, emits human-readable status block, logs Trackio event (if credentials), optionally pushes to HF Hub.

**Independent Test**: Run one Worker loop to produce at least one CSV row; invoke `@reporter`; verify status block includes best F1, experiment index, strategy name, staircase chart path.

### Validation for US5

- [x] T075 [P] [US5] Write pytest test `repos/fungal-cv-qdrant/tests/test_reporter_output.py` — mock CSV with 3 rows, verify reporter summary parser extracts best F1 correctly
- [x] T076 [US5] Run reporter test: `uv --directory repos/fungal-cv-qdrant run pytest tests/test_reporter_output.py -v`
- [ ] T077 [US5] **[TEST]** Run `opencode run "ask reporter agent to summarize retrieval experiment status"` — verify output matches expected format (best F1, active workers, chart path)
- [ ] T078 [US5] Graceful degradation test: invoke `@reporter` without `TRACKIO_API_KEY` env var; verify it skips Trackio cleanly and still produces status block

### Implementation for US5

- [x] T079 [US5] Verify `reporter.md` frontmatter: `model: 9router/MiniBrain`, edit: deny, bash permissions read-only
- [x] T080 [US5] Document Trackio integration in `quickstart.md`: what `TRACKIO_API_KEY` env var enables, how to set it

**Checkpoint**: Reporter produces correct status for any completed experiment state. Degrades gracefully without credentials.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation sync, AGENTS.md update, PR evidence, final validation.

- [x] T081 [P] Update `AGENTS.md` with: new agent listing (autolab/researcher/planner/worker/reporter), model tier table, `opencode run "test"` command, worktree lifecycle notes
- [x] T082 [P] Update `repos/fungal-cv-qdrant/README.md` with: Autolab multi-agent system section, quickstart usage, research notebook layout
- [x] T083 [P] Sync `specs/004-autolab-multi-agent/quickstart.md` — ensure all commands match final implementation
- [x] T084 [P] Verify `.opencode/opencode.json` is valid JSON: `python3 -c "import json; json.load(open('.opencode/opencode.json'))"`
- [x] T085 [P] Verify all agent `.md` files have valid YAML frontmatter: check `description`, `mode`, `model` fields present in each of the 5 new agents
- [ ] T086 **[TEST]** Final `opencode run "test"` run: confirm all pytest suites pass (`test_experiment_contract.py`, `test_worker_isolation.py`, `test_csv_append.py`, `test_research_notebook.py`, `test_planner_queue.py`, `test_reporter_output.py`)
- [x] T087 **[TEST]** Full `uv --directory repos/fungal-cv-qdrant run pytest tests/ -q` — all tests pass, no regressions (92 passed)
- [x] T088 **[TEST]** `uv --directory repos/fungal-cv-qdrant run ruff check src/` — no lint errors
- [x] T089 **[TEST]** `uv --directory repos/fungal-cv-qdrant run mypy src/experiments/retrieval/ src/experiments/threshold/ --ignore-missing-imports` — no type errors
- [ ] T090 [P] Manual end-to-end Autolab loop: launch opencode in monorepo root, invoke `@autolab` with "run one autoresearch pass on retrieval", capture log showing Researcher entry → Planner queue → Worker run → Reporter summary
- [ ] T091 [P] Staircase chart screenshot for PR evidence: confirm `results/autoresearch/retrieval.png` updated and compliant with visualization rules
- [ ] T092 [P] F1 comparison table for PR: restructured `retrieval` + `threshold` F1 vs baseline (T018 baseline)
- [ ] T093 Create PR with evidence: spec + plan + tasks links, validation log excerpt, staircase screenshot, F1 comparison table, remaining risks

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user story phases
- **Phase 3 (US6 — remaining packages)**: Depends on Phase 2 (pattern established); can parallelize with Phase 4
- **Phase 4 (US3 — Worker)**: Depends on Phase 2 (needs `run()` contract); can parallelize with Phase 3
- **Phase 5 (US1 — Autolab loop)**: Depends on Phase 4 (Worker must exist); depends on Phase 2 (experiment packages)
- **Phase 6 (US2 — Researcher)**: Depends on Phase 1 only (reads research notebook); can parallelize with Phases 3+4
- **Phase 7 (US4 — Planner)**: Depends on Phase 6 (reads `paper-ideas.md`); can start once Phase 6 Researcher format is established
- **Phase 8 (US5 — Reporter)**: Depends on Phase 4 Worker producing CSV rows; can parallelize with Phase 6+7
- **Phase 9 (Polish)**: Depends on all user story phases complete

### User Story Dependencies

- **US6 (P1 — package restructure)**: No story dependency — only foundational work needed
- **US3 (P1 — Worker)**: Depends on US6 (needs `run()` contract to call)
- **US1 (P1 — Autolab loop)**: Depends on US3 (Worker) + US6 (packages)
- **US2 (P2 — Researcher)**: Independent of US3/US6 — only needs research notebook files
- **US4 (P2 — Planner)**: Depends on US2 (reads `paper-ideas.md` format)
- **US5 (P3 — Reporter)**: Depends on US3 (needs CSV rows to read)

### Parallel Opportunities

- T001–T010 (Phase 1): most run in parallel
- T019+T022 (both package restructures): fully parallel
- T030–T036 (remaining 7 packages): fully parallel
- T038+T059+T075 (test writing across stories): parallel across stories
- T081–T085 (Polish documentation): all parallel

---

## Parallel Example: Phase 2 Foundational

```bash
# Run in parallel:
Task T019: Create ExperimentParams/ExperimentResult in retrieval/run.py
Task T022: Create ExperimentParams/ExperimentResult in threshold/run.py

# Then in parallel:
Task T020: Wrap retrieval logic in run()
Task T023: Wrap threshold logic in run()

# Then:
Task T021: Create retrieval/cli.py
Task T024: Create threshold/cli.py

# Validate in parallel:
Task T011: Import test retrieval
Task T012: Import test threshold
Task T013: Ruff check both packages
Task T014: Mypy check both packages
```

---

## Testing Plan Summary

| Test File | Coverage | Command |
|-----------|----------|---------|
| `tests/test_experiment_contract.py` | `run()` interface + `ExperimentResult` shape for all packages | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_experiment_contract.py -v` |
| `tests/test_worker_isolation.py` | Two concurrent Workers → non-overlapping output | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_worker_isolation.py -v` |
| `tests/test_csv_append.py` | Lock-safe CSV append under concurrent access | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_csv_append.py -v` |
| `tests/test_research_notebook.py` | `paper-ideas.md` entry parser (required fields) | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_research_notebook.py -v` |
| `tests/test_planner_queue.py` | Planner dedup logic: pending→in-progress, skip in-progress | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_planner_queue.py -v` |
| `tests/test_reporter_output.py` | Reporter summary parser: best F1 extraction from CSV | `uv --directory repos/fungal-cv-qdrant run pytest tests/test_reporter_output.py -v` |
| Full suite | All above | `uv --directory repos/fungal-cv-qdrant run pytest tests/ -q` |

**`opencode run "test"` command** (registered in T054 at `.opencode/commands/test.md`):
```bash
uv --directory repos/fungal-cv-qdrant run pytest tests/ -q && \
uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/
```

**OpenCode agent smoke tests** (using `opencode run "<prompt>"`):
- T009: agent registration check
- T010: `hypothesis-validator` tool smoke test
- T017: `experiment-test-runner` tool smoke test
- T042: Worker agent invocation smoke test
- T048: Full Autolab loop smoke test
- T053/T055: `opencode run "test"` command verification
- T060: Researcher agent paper fetch
- T070: Planner queue invocation
- T077: Reporter status summary
- T086: Final `opencode run "test"` confirmation

---

## Implementation Strategy

### MVP Scope (P1 Stories Only)

1. Phase 1: Setup
2. Phase 2: Foundational (`retrieval` + `threshold` restructure)
3. Phase 4: Worker Agent
4. Phase 5: Autolab Loop (US1)
5. **STOP and VALIDATE**: `opencode run "test"` passes; manual Autolab loop completes

### Incremental Delivery

1. Phases 1+2 → experiment contract established, tests pass
2. Phase 3 → all 9 packages restructured
3. Phase 4 → Worker runs safely in isolation
4. Phase 5 → Autolab orchestrates end-to-end (MVP!)
5. Phase 6 → Researcher adds literature-backed hypotheses
6. Phase 7 → Planner automates queue management
7. Phase 8 → Reporter surfaces results automatically
8. Phase 9 → Polish, PR

### Risk Mitigations

| Risk | Mitigation |
|------|------------|
| `prepare.py` dependency breaks after restructure | Baseline F1 comparison (T018+T026) — must match before merge |
| Concurrent CSV append corruption | `fcntl.flock` unit test (T044+T045) — run before any Worker PR |
| Agent description not triggering correct subagent | `opencode run` smoke tests (T009, T010, T042) early in Phase 1 |
| Worktree accumulation after failures | `worktree-janitor` subagent in backlog; manual cleanup documented in quickstart |

---

## Notes

- `[P]` = different files/independent execution, safe to parallelize
- `[US#]` = maps to user story for traceability
- `**[TEST]**` = uses `opencode run "<prompt>"` to validate agent/tool behavior via the CLI
- Each user story is independently completable and testable
- `prepare.py` MUST NOT be modified — all new capability via `run.py` + `cli.py`
- `results.tsv` + `paper-ideas.md` use file locking or sequential write patterns — no concurrent markdown writes
- Commit after each Phase checkpoint
