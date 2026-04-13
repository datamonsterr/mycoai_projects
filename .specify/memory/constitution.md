<!--
Sync Impact Report
Version change: 1.1.0 -> 1.2.0
Modified principles:
- III. Pipeline-to-Product Traceability -> III. Pipeline-to-Product Traceability and Reimplementation
- IV. Context-Specific Verification -> IV. Context-Specific Verification and Delivery Evidence
- VI. Canonical Toolchains -> VI. Canonical Toolchains
- Added: VII. Autonomous Delivery and Definition of Done
Added sections:
- None
Removed sections:
- None
Templates requiring updates:
- ✅ updated: .specify/templates/plan-template.md
- ✅ updated: .specify/templates/spec-template.md
- ✅ updated: .specify/templates/tasks-template.md
- ✅ checked: .specify/templates/commands/ (no command templates present)
- ✅ updated: AGENTS.md
- ✅ updated: CLAUDE.md
- ✅ updated: .opencode/command/speckit.implement.md
Follow-up TODOs:
- None
-->
# MycoAI Monorepo Constitution

## Core Principles

### I. Experiment and Product Boundaries
`fungal-cv-qdrant` MUST own experiment logic, experiment reports, and artifact
generation. `mycoai_retrieval_backend` MUST own service, indexing, and API
behavior. `mycoai_retrieval_frontend` MUST own scientist-facing UI and
visualization behavior. Shared runtime data at the monorepo root MUST be
treated as consumed artifacts, not as a place to hide business logic or
duplicate pipeline code.

Rationale: clear ownership keeps research iteration and product delivery from
drifting into each other.

### II. Experiment Contract Discipline
Autoresearch work MUST start from the experiment `program.md`, preserve the
established `fungal-cv-qdrant/src/prepare.py` invocation contract, keep attempt
logging append-only, and follow the staircase visualization and branch naming
rules defined in `.opencode/rules/`. Experiment attempts MUST favor
qualitatively different strategies over repeated parameter churn. New best
results MAY be merged to the canonical `autoresearch/{experiment-name}` branch;
discarded attempts MUST remain historical record only.

Rationale: experiment results are only useful when every run is reproducible,
comparable, and traceable.

### III. Pipeline-to-Product Traceability and Reimplementation
Any backend or frontend feature that depends on outputs from
`fungal-cv-qdrant/src/experiments/retrieval/` or
`fungal-cv-qdrant/src/experiments/kmeans_segmentation/` MUST identify the
producing command, output artifact, and consuming API or UI surface in its
spec, plan, and tasks. Product repos MAY inspect experiment code to understand
algorithms, parameters, and expected outputs, but they MUST reimplement product
behavior inside the owning repo. Product repos MUST NOT import modules,
helpers, or runtime code directly from `fungal-cv-qdrant`. Integration between
repos MUST happen through validated artifacts, schemas, or documented payloads.
When a pipeline contract changes, producer and consumer documentation MUST be
updated in the same change.

Rationale: the system only stays trustworthy when scientist-facing behavior can
be traced back to validated experiment outputs without creating hidden runtime
coupling between research and product repos.

### IV. Context-Specific Verification and Delivery Evidence
Every change MUST include verification in each touched context and MUST name the
exact commands or checks using the repo's canonical toolchain. Experiment
changes MUST run the relevant `uv --directory fungal-cv-qdrant ...` command or
check, validate affected logs or artifacts, and keep reports current. Backend
changes MUST run the relevant Ruff, format check, MyPy, and Pytest commands
through `uv`. Frontend changes MUST run the relevant lint, typecheck, and build
commands through `pnpm`, and MUST add automated unit or end-to-end coverage for
behavior changes or explicitly record why narrower validation is sufficient.
User-facing changes MUST include a manual browser or API journey check and MUST
record what path was exercised.

Rationale: this monorepo crosses research, API, and UI boundaries, so
validation must happen where the risk is introduced and must produce evidence
that the final behavior matches the intended workflow.

### V. Minimal Safe Change
Changes MUST be the smallest correct change within the owning repo, preserve
existing shared data path conventions, and avoid new compatibility layers,
duplicate pipelines, or cross-repo coupling unless a concrete operational need
is documented. Shared runtime assets under `Dataset/`, `results/`, `weights/`,
and `species_weights.json` MUST remain consumable by all repos after the
change.

Rationale: minimal changes reduce accidental regressions across submodules and
keep experiment outputs usable by the system.

### VI. Canonical Toolchains
Python dependency installation, environment sync, and Python CLI execution MUST
use `uv`, `uv run`, `uv sync`, `uv add`, or `uvx` as appropriate. Frontend
package installation and script execution MUST use `pnpm`. GitHub workflow,
checks, and pull request automation MUST use `gh`. New active repo guidance,
templates, scripts, or CI steps MUST NOT introduce raw `pip`, `python -m pip`,
or `npm` commands.

Rationale: one canonical toolchain per ecosystem keeps local, CI, and agent
workflows reproducible and prevents avoidable environment drift.

### VII. Autonomous Delivery and Definition of Done
Primary delivery agents and implementation workflows MUST carry planned work
through implementation, local verification, relevant workflow verification when
available, manual validation for user-facing behavior, and PR-ready evidence
before declaring the change done. A change is not done until failing checks are
fixed or explicitly reported, the definition-of-done evidence is summarized,
and remaining risks are called out. Autonomous agents MAY open a PR only after
these gates pass and the PR body names the spec, plan, validation evidence, and
consumer or producer contract effects.

Rationale: autonomous delivery is only trustworthy when it closes the loop from
specification through validation and review handoff.

## Project Boundaries and Data Contracts

- `fungal-cv-qdrant/` owns dataset preparation, segmentation, retrieval
  evaluation, experiment reports, and Qdrant-facing research outputs.
- `mycoai_retrieval_backend/` owns API contracts, data management workflows,
  indexing orchestration, and product-side consumption of validated experiment
  outputs.
- `mycoai_retrieval_frontend/` owns search, browsing, and visualization flows
  presented to mycologists and other scientist users.
- Root-level `Dataset/`, `results/`, `weights/`, and `species_weights.json`
  are shared runtime assets. They MUST NOT become a second code location or an
  undocumented integration surface.
- Any feature spanning experiment and product code MUST name the upstream
  producer, the exchanged artifact or schema, the downstream consumer, and any
  experiment source path consulted for product-side reimplementation before
  implementation begins.
- Product repos MUST NOT add direct path, package, or runtime imports from
  `fungal-cv-qdrant/`.

## Delivery Workflow, Testing, and Quality Gates

1. Classify each change as experiment, backend, frontend, or shared-contract
   work before editing code.
2. Specs MUST identify touched repos, affected shared artifacts, the canonical
   package and command toolchain, any dependency on `retrieval` or
   `kmeans_segmentation` outputs, and any experiment source reviewed for
   product-side reimplementation.
3. Plans MUST pass a Constitution Check covering ownership boundaries,
   traceability, no direct cross-repo imports, canonical toolchains, required
   commands, test strategy, manual validation needs, and documentation updates.
4. Tasks MUST include explicit verification work for every touched repo,
   explicit contract-sync work for any cross-boundary change, and manual or
   end-to-end verification tasks whenever user-facing behavior or external
   contracts change. Command tasks MUST use `uv`/`uvx`, `pnpm`, or `gh` as
   appropriate.
5. Product-side implementations derived from experiments MUST translate logic
   into the backend or frontend repo, add local tests around the translation,
   and point back to the analyzed experiment path in docs or comments when the
   mapping would otherwise be unclear.
6. Autonomous delivery flows MUST iterate on failing local tests or workflow
   checks before requesting review or opening a PR.
7. Reviews MUST reject changes that move logic into the wrong repo, import from
   `fungal-cv-qdrant` into product repos, drift from canonical toolchains, skip
   validation, or leave experiment outputs and consumers out of sync.
8. When a change alters user-visible behavior or consumption of experiment
   outputs, the relevant README, agent guidance, and PR summary MUST be updated
   in the same change set.

## Governance

This constitution supersedes informal local practice for the MycoAI monorepo.
Amendments MUST be made in the same change set as any updates to
`.specify/templates/*.md` and any runtime guidance made inconsistent by the
amendment.

Versioning policy is semantic:

- MAJOR for removing a principle or redefining an existing governance
  requirement in a backward-incompatible way.
- MINOR for adding a new principle, a new mandatory section, or materially
  expanding required workflow.
- PATCH for clarifications, wording improvements, or non-semantic template
  alignment.

Compliance review is mandatory for every spec, plan, task list, and code
review. Reviewers MUST confirm repo ownership, experiment-to-product
traceability, product-side reimplementation boundaries, canonical toolchain
usage, validation evidence, definition-of-done evidence, and documentation sync
before approval.

Operational guidance in `AGENTS.md`, `CLAUDE.md`,
`.opencode/agents/autoresearch.md`, `fungal-cv-qdrant/README.md`,
`mycoai_retrieval_backend/README.md`, and `mycoai_retrieval_frontend/README.md`
MAY elaborate workflow details but MUST NOT contradict this constitution.

**Version**: 1.2.0 | **Ratified**: 2026-04-12 | **Last Amended**: 2026-04-13
