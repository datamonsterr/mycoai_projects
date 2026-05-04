# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` or `[autoresearch/<experiment-name>/<N>-<summary>]` for `fungal-cv-qdrant` autoresearch only | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Package / Command Tooling**: [e.g., `uv` + `uvx` for Python, `pnpm` for frontend, or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [e.g., library/cli/web-service/mobile-app/compiler/desktop-app or NEEDS CLARIFICATION]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [ ] Ownership is explicit: each touched path belongs to the correct repo
      (`fungal-cv-qdrant`, backend, frontend, or shared root assets).
- [ ] Traceability is explicit: any dependency on `retrieval` or
      `kmeans_segmentation` names the producer command, artifact, and consumer.
- [ ] Reimplementation is explicit: backend or frontend work may inspect
      `fungal-cv-qdrant` as reference only and MUST NOT import code from it.
- [ ] Canonical toolchains are explicit: Python work uses `uv`/`uvx`, frontend
      work uses `pnpm`, and GitHub automation uses `gh`; any exception is
      documented.
- [ ] Validation is explicit: list the exact commands or checks that will run
      in every touched repo.
- [ ] Definition of done is explicit: name the required unit, integration,
      e2e, manual, and workflow checks for the touched surface.
- [ ] Contract sync is explicit: identify README, agent, or schema updates
      required for producer and consumer alignment.
- [ ] Minimality is justified: any new shared schema, compatibility layer, or
      cross-repo coupling is called out and defended.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
repos/fungal-cv-qdrant/
├── src/experiments/
├── src/analysis/
└── report/

repos/mycoai_retrieval_backend/
├── src/
└── tests/

repos/mycoai_retrieval_frontend/
├── src/
└── [tests or app-specific validation paths]

Dataset/
results/
weights/
species_weights.json
```

**Structure Decision**: [Name the touched repo(s), the exact directories to be
edited, and any artifact boundary crossed between experiment and product code]

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
