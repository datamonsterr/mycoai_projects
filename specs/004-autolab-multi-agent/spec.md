# Feature Specification: Autolab Multi-Agent System for fungal-cv-qdrant

**Feature Branch**: `004-autolab-multi-agent`
**Created**: 2026-05-05
**Status**: Draft
**Input**: User description: "I want to setup @.opencode/ for @.opencode/agents/autoresearch.md subagent: 1. Researcher: Has ability to get information on the internet, research paper, use markitdown to save and analyze the paper. Analyze the topic to get the best match paper, extract the methodology from the paper, validate that it fits our case, dataset, create report synthesize all findings in the papers. This agent define a research experiment. 2. Planner: Central coordiantor that owns the experiment queue 3. Worker: modify our @.opencode/agents/autoresearch.md agent to be the worker who will own one git worktree and one hypothesis. 4. Reporter: Agent observes process, running trackio, sync Hugging face status if needed 5. Autolab: the primary agent for user to interact with the whole workflow. This is apply for @repos/fungal-cv-qdrant/ project. Analyze the current repo and restructure @repos/fungal-cv-qdrant/src/experiments/ based on https://github.com/burtenshaw/multiautoresearch this setup."

## Table of Contents

- [Affected Contexts](#affected-contexts)
- [User Scenarios & Testing](#user-scenarios--testing)
- [Requirements](#requirements)
- [Success Criteria](#success-criteria)
- [Definition of Done](#definition-of-done)
- [Assumptions](#assumptions)

## Affected Contexts *(mandatory)*

- **Primary Repo**: `repos/fungal-cv-qdrant`
- **Additional Touched Repos**: monorepo root `.opencode/` (agent config layer); `repos/mycoai_retrieval_backend` and `repos/mycoai_retrieval_frontend` not directly touched but consume validated artifacts from restructured experiments
- **Shared Artifacts**: `results/`, `weights/`, `Dataset/`, monorepo root `species_weights.json`; per-experiment run ledger at `results/autoresearch/{experiment}.csv`
- **Execution Tooling**: `uv`/`uvx` for Python contexts; `git worktree` for isolated worker branches; `gh` for PR checks; `hf` CLI for Hugging Face Jobs sync; `trackio` for experiment observation
- **Experiment Dependency**: All 5 agents operate on experiments under `repos/fungal-cv-qdrant/src/experiments/`; Researcher defines new experiment packages; Worker runs `prepare.py` inside isolated worktrees; Reporter reads result artifacts; downstream backend/frontend consume validated `retrieval/` and `kmeans_segmentation/` outputs
- **Reimplementation Boundary**: This feature modifies experiment infrastructure within `repos/fungal-cv-qdrant`; it does not export code to backend/frontend; those repos must not import from this repo

## User Scenarios & Testing *(mandatory)*

### User Story 1 - End-to-End Autonomous Experiment Loop via Autolab (Priority: P1)

A scientist opens OpenCode in the monorepo root and asks the `autolab` primary agent to "research top fungal retrieval improvements, propose experiments, run workers, and summarize results." The full Researcher → Planner → Worker → Reporter loop completes without manual intervention. The scientist receives a final summary with staircase chart and a short report.

**Why this priority**: This is the primary delivery value. All other agents are useless without the orchestration working end-to-end.

**Independent Test**: Can be fully tested by launching `opencode` in `repos/fungal-cv-qdrant/`, activating `autolab` agent with one-line prompt, and verifying that at minimum one Worker run completes, emits a score, and Reporter logs it.

**Acceptance Scenarios**:

1. **Given** monorepo set up with `uv sync` and `mise install`, **When** scientist prompts `autolab` agent with "run one autoresearch pass on retrieval experiment", **Then** Planner queues at least one hypothesis, Worker creates a worktree, runs `prepare.py`, and Reporter appends the result to the experiment log
2. **Given** a completed Worker run, **When** Reporter observes it, **Then** staircase chart at `results/autoresearch/retrieval.png` is updated and a Trackio event is logged
3. **Given** multiple experiments queued by Planner, **When** all Workers finish, **Then** Autolab surfaces the best result and its source hypothesis to the scientist

---

### User Story 2 - Researcher Identifies and Synthesizes Relevant Papers (Priority: P2)

A scientist asks the `researcher` agent to "find papers relevant to fungal species retrieval using feature embeddings." Researcher searches the internet, downloads PDFs, converts to markdown via markitdown, extracts methodology, validates fit against the current dataset and experiment structure, and outputs a `research/paper-ideas.md` file plus a suggested experiment definition.

**Why this priority**: Literature-backed hypotheses yield higher-quality experiments; however, the loop still functions without this agent (Worker can use heuristic strategies).

**Independent Test**: Can be fully tested by invoking `researcher` agent directly with a research topic and verifying `research/paper-ideas.md` is created/updated with at least one structured entry including paper title, methodology summary, fit assessment, and a proposed `program.md` snippet.

**Acceptance Scenarios**:

1. **Given** a research topic prompt, **When** researcher agent searches and retrieves a paper, **Then** paper is converted to markdown and stored under `research/papers/`
2. **Given** a downloaded paper, **When** researcher extracts methodology, **Then** it produces a structured entry in `research/paper-ideas.md` with: paper title, methodology summary, fit-to-dataset assessment, and a proposed experiment hypothesis
3. **Given** a proposed hypothesis, **When** Planner reads `research/paper-ideas.md`, **Then** Planner can enqueue the hypothesis without further translation

---

### User Story 3 - Worker Owns One Worktree, One Hypothesis (Priority: P1)

The `worker` agent (derived from existing `autoresearch.md`) receives a single hypothesis from Planner, creates an isolated git worktree, modifies `run_accuracy.py` within that worktree, runs `prepare.py`, records the result, and exits without touching the main checkout or other workers' worktrees.

**Why this priority**: Isolation is the core safety property; without it multi-worker runs corrupt shared state.

**Independent Test**: Can be fully tested by manually invoking `worker` agent with a hypothesis, verifying a new worktree at `.runtime/worktrees/<experiment-id>/` is created, `prepare.py` completes, and the experiment log is appended without modifying `main` working tree files.

**Acceptance Scenarios**:

1. **Given** a hypothesis from Planner, **When** worker agent starts, **Then** it creates a git worktree under `.runtime/worktrees/<experiment-id>/` and checks out a branch following `autoresearch/{experiment}/{N}-{summary}` convention
2. **Given** an isolated worktree, **When** worker modifies `run_accuracy.py` and runs `prepare.py`, **Then** modifications are confined to that worktree and do not affect files in the main `repos/fungal-cv-qdrant/` checkout
3. **Given** `prepare.py` completes, **When** worker records the result, **Then** it appends one row to `results/autoresearch/{experiment}.csv` at the monorepo root, logs to `results/{experiment}/log/experiments.log`, and exits cleanly
4. **Given** a worker run that fails, **When** the exception is raised, **Then** worker logs the failure and does not corrupt the shared log or worktree of any other active worker

---

### User Story 4 - Planner Coordinates Experiment Queue (Priority: P2)

The `planner` agent maintains a queue of hypotheses sourced from `researcher` output and manual scientist input. It assigns one hypothesis per available worker slot, tracks in-progress and completed experiments, prevents duplicate hypotheses from running, and updates `research/results.tsv` with final outcomes.

**Why this priority**: Without a coordinator, workers could duplicate work or exhaust GPU resources simultaneously.

**Independent Test**: Can be fully tested by populating `research/paper-ideas.md` with two entries and invoking `planner`, then verifying it creates exactly two worker worktrees (one per entry), not more, and updates status when each completes.

**Acceptance Scenarios**:

1. **Given** a list of pending hypotheses, **When** planner assigns work, **Then** each hypothesis is assigned to exactly one worker and recorded as in-progress
2. **Given** a hypothesis already completed or in-progress, **When** planner processes the queue, **Then** it skips the duplicate without creating a new worker
3. **Given** all workers finished, **When** planner reviews outcomes, **Then** it surfaces the best result and notifies autolab

---

### User Story 5 - Reporter Observes and Surfaces Experiment Status (Priority: P3)

The `reporter` agent monitors active and completed Workers, syncs status to Trackio, optionally syncs artifacts to Hugging Face Hub, and emits a concise summary of the current best result, active jobs, and anomalies.

**Why this priority**: Observability is a quality-of-life feature; the core loop functions without it.

**Independent Test**: Can be fully tested by having one completed Worker run then invoking `reporter`, verifying it outputs a human-readable status block referencing the latest log entry, staircase chart path, and Trackio event ID.

**Acceptance Scenarios**:

1. **Given** one or more completed Worker runs, **When** reporter is invoked, **Then** it reads `results/autoresearch/{experiment}.csv` and emits a summary with: current best F1, experiment index, strategy name, and path to staircase chart
2. **Given** Trackio credentials available, **When** reporter runs, **Then** it logs a Trackio event with experiment metadata
3. **Given** Hugging Face credentials available and sync requested, **When** reporter syncs, **Then** artifact artifacts under `results/` are pushed to the configured HF Hub repo

---

### User Story 6 - Experiment Package Restructure for Agent Compatibility (Priority: P1)

The 9 existing experiment packages under `repos/fungal-cv-qdrant/src/experiments/` are restructured to expose a uniform per-package contract: a `run(params) -> Result` function, a `cli.py` entrypoint, isolated output roots via injected `output_root/run_id`, and a machine-readable manifest. This contract is the boundary through which all agents interact with experiments.

**Why this priority**: Without this restructure, workers cannot run experiments safely in parallel, and Planner cannot read outcomes reliably.

**Independent Test**: Can be fully tested by running the restructured `retrieval` and `threshold` experiments from a worktree with a unique `run_id` parameter and verifying output lands in `results/<run_id>/` not the global `results/` root.

**Acceptance Scenarios**:

1. **Given** a restructured experiment package, **When** called with a unique `run_id`, **Then** all output artifacts land under `results/<run_id>/` and no files are written to global shared paths
2. **Given** two Worker agents running the same experiment with different `run_id` values simultaneously, **Then** neither corrupts the other's output
3. **Given** a restructured `retrieval` package, **When** its uniform `run()` interface is called, **Then** it returns a typed result object containing: F1 score, artifact paths, and strategy name

---

### Edge Cases

- What happens when a Worker's worktree branch conflicts with an existing branch? → Worker MUST detect conflict and report to Planner before proceeding.
- What happens when Researcher cannot access the internet or a paper URL is unavailable? → Researcher logs the failure and continues with cached or previously downloaded papers.
- What happens when `prepare.py` crashes mid-run inside a Worker worktree? → Worker catches the exception, logs it, and marks the hypothesis as failed in the queue without deleting the worktree (preserves debug state).
- What happens when two Workers attempt to append to `results/autoresearch/{experiment}.csv` simultaneously? → Write operations MUST be serialized (file lock or atomic append) to prevent corruption.
- What happens when Planner receives more hypotheses than available GPU/CPU slots? → Planner queues excess hypotheses and only creates workers up to the configured concurrency limit.

## Requirements *(mandatory)*

### Functional Requirements

**Agent Definitions**

- **FR-001**: System MUST provide an `autolab` primary agent in `.opencode/agents/autolab.md` that serves as the single entry point for scientists to orchestrate the full research loop
- **FR-002**: System MUST provide a `researcher` agent in `.opencode/agents/researcher.md` capable of web search, PDF download, markitdown conversion, methodology extraction, fit validation, and outputting structured `research/paper-ideas.md` entries
- **FR-003**: System MUST provide a `planner` agent in `.opencode/agents/planner.md` that reads `research/paper-ideas.md`, maintains an experiment queue, assigns hypotheses to workers, prevents duplicates, and tracks outcomes in `research/results.tsv`
- **FR-004**: System MUST provide a `worker` agent derived from the existing `.opencode/agents/autoresearch.md`, updated to accept a hypothesis from Planner, create an isolated git worktree under `.runtime/worktrees/`, run `prepare.py` within it, and exit cleanly
- **FR-005**: System MUST provide a `reporter` agent in `.opencode/agents/reporter.md` that reads experiment logs, emits a status summary, logs to Trackio when credentials are available, and optionally syncs artifacts to Hugging Face Hub
- **FR-006**: The `worker` agent MUST follow the existing branch naming convention `autoresearch/{experiment-name}/{N}-{summary}` defined in `.opencode/rules/branch-naming.md`

**Worktree Management**

- **FR-007**: System MUST use `git worktree add` to create isolated per-hypothesis worktrees under `.runtime/worktrees/<experiment-id>/` inside `repos/fungal-cv-qdrant/`
- **FR-008**: System MUST clean up completed worktrees after outcomes are recorded, unless the worktree produced a new best result (retained for merge)
- **FR-009**: System MUST prevent more than the configured `MAX_CONCURRENT_WORKERS` worktrees from existing simultaneously

**Experiment Package Contract**

- **FR-010**: Each experiment package under `repos/fungal-cv-qdrant/src/experiments/` MUST expose a `run(params: ExperimentParams) -> ExperimentResult` function that is importable without side effects
- **FR-011**: Each `ExperimentResult` MUST contain: `f1_score: float`, `strategy_name: str`, `artifact_paths: list[str]`, `run_id: str`
- **FR-012**: Each experiment package MUST accept an `output_root` parameter so that all file writes are scoped to `results/<run_id>/` rather than global paths
- **FR-013**: Each experiment package MUST provide a `cli.py` module that wraps `run()` for direct invocation via `uv run python -m src.experiments.<name>.cli`
- **FR-014**: The existing `retrieval` and `threshold` packages MUST be restructured first as the highest-priority targets; remaining packages (`cross_validation`, `feature_extraction`, `finetune_dl`, `kmeans_segmentation`, `yolo_cross_validation`, `yolo_dataset`, `yolo_segmentation`) follow in a second pass

**Research Notebook**

- **FR-015**: System MUST maintain `research/paper-ideas.md` as the canonical structured list of paper-derived hypotheses, with fields: paper title, URL, methodology summary, fit assessment, status (`pending`/`in-progress`/`completed`/`rejected`), and proposed strategy
- **FR-016**: System MUST maintain `research/results.tsv` as an append-only run ledger with columns: `timestamp`, `experiment`, `run_id`, `strategy`, `f1_score`, `is_new_best`, `worker_branch`
- **FR-017**: System MUST maintain `research/do-not-repeat.md` listing hypotheses that have been tried and should not be re-attempted

**Staircase Visualization**

- **FR-018**: Staircase chart generation MUST continue to follow the rules defined in `.opencode/rules/experiment-visualization.md` after restructure

### Key Entities *(include if feature involves data)*

- **Hypothesis**: A proposed strategy change with source (paper or heuristic), target experiment name, and description
- **ExperimentQueue**: Ordered list of pending hypotheses maintained by Planner; serialized to `research/results.tsv`
- **WorkerWorktree**: An isolated git worktree tied to one hypothesis and one branch; lives at `.runtime/worktrees/<experiment-id>/`
- **ExperimentResult**: Typed output of one `run()` call; contains F1 score, artifacts, run_id, strategy name
- **ResearchPaper**: A downloaded and markitdown-converted paper stored at `research/papers/<slug>.md` with associated structured entry in `research/paper-ideas.md`

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Scientist can issue one natural-language prompt to `autolab` and receive at least one completed experiment result within a single OpenCode session, without manual script invocation
- **SC-002**: At least two Worker agents can run the same experiment concurrently on different hypotheses without corrupting shared output files, validated by comparing output under `results/<run_id>/`
- **SC-003**: Researcher agent successfully converts at least one real paper to a structured `research/paper-ideas.md` entry that Planner can read without modification
- **SC-004**: Restructured `retrieval` and `threshold` experiment packages produce identical F1 scores to pre-restructure baselines when called with equivalent parameters
- **SC-005**: Staircase chart at `results/autoresearch/{experiment}.png` is updated after every Worker run and remains compliant with the existing visualization rules
- **SC-006**: Reporter produces a human-readable status summary for any completed experiment without requiring additional manual input

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**:
  - `uv --directory repos/fungal-cv-qdrant run pytest tests/` passes with no regressions on restructured experiment packages
  - `uv --directory repos/fungal-cv-qdrant run ruff check src/experiments/` passes
  - `uv --directory repos/fungal-cv-qdrant run mypy src/experiments/retrieval/ src/experiments/threshold/` passes
  - Running two concurrent Worker agents on `retrieval` with distinct `run_id` values produces non-overlapping output under `results/`
- **Workflow Checks**: Relevant `repos/fungal-cv-qdrant/.github/` workflows pass on PR; if no CI is configured, document this explicitly in PR
- **Manual Validation**: Scientist-facing end-to-end test: launch `opencode` in `repos/fungal-cv-qdrant/`, invoke `autolab` with one-line research prompt, confirm Reporter summary is produced and staircase chart is updated
- **PR Evidence**: PR must include: screenshot or log of one complete Autolab loop (prompt → Researcher entry → Planner queue → Worker run → Reporter summary), F1 comparison table for restructured packages vs baseline, and staircase chart screenshot

## Assumptions

- The existing `prepare.py` in `repos/fungal-cv-qdrant/` remains immutable per project convention; agents call it but never modify it
- `uv run python src/prepare.py --experiment {name} --description "..."` remains the canonical Worker invocation
- Trackio credentials and Hugging Face credentials are optional; Reporter degrades gracefully if absent
- Maximum concurrent workers defaults to 2 (local machine resources); `MAX_CONCURRENT_WORKERS` is configurable per session
- `git worktree` is available in the environment (part of standard git)
- Web search capability for Researcher is provided by the MCP or tool configuration already available to the agent; this spec does not require adding new MCP servers
- The multiautoresearch reference repo (`burtenshaw/multiautoresearch`) is used as structural inspiration for the multi-agent role separation and research notebook layout, not as code to import directly
- The restructure of experiment packages is done incrementally: `retrieval` and `threshold` first, remaining packages in a follow-up; this spec covers the full target state but implementation is phased
- `.runtime/worktrees/` is added to `.gitignore` to avoid tracking ephemeral worktree files
- Existing staircase chart and CSV logging infrastructure at `results/autoresearch/` remains unchanged
