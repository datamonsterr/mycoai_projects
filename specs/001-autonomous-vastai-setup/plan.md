# Implementation Plan: Autonomous Vast.ai Setup

**Branch**: `001-vastai-workspace-sync` | **Date**: 2026-04-21 | **Spec**: `/home/dat/dev/mycoai/worktrees/001-vastai-workspace-sync/specs/001-autonomous-vastai-setup/spec.md`
**Input**: Feature specification from `/specs/001-autonomous-vastai-setup/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Improve the existing monorepo-level Vast.ai workflow so a developer or agent can provision or reuse a remote workspace, validate it, and attach from VS Code with minimal manual work. The implementation will extend the current root `tools/workspace_bootstrap.sh` flow, add connection-oriented outputs and recovery guidance, and update root/operator documentation plus `.opencode/commands/` so setup, reconnect, and VS Code access are repeatable and low-interaction.

## Technical Context

**Language/Version**: Bash + Python 3.13 + Markdown documentation  
**Primary Dependencies**: OpenSSH, git with submodules, `mise`, `uv`, optional `vastai` CLI for instance lookup, VS Code Remote-SSH, existing `tools/workspace_bootstrap.sh` and `tools/dataset_sync.py`  
**Package / Command Tooling**: `uv`/`uvx` for Python execution, `mise` for shared tool install, `gh` for any workflow verification, shell entrypoints under `tools/`  
**Storage**: Monorepo root filesystem (`Dataset/`, `results/`, `weights/`, `species_weights.json`), local SSH config on the developer machine, optional external `rclone` config for dataset access  
**Testing**: `bash -n tools/workspace_bootstrap.sh`, relevant Python tests via `uv run --with pytest pytest tools/tests/test_dataset_sync.py`, documentation command consistency review, manual first-time setup, manual reconnect/recovery, manual VS Code Remote-SSH attach  
**Target Platform**: Linux remote workspace on Vast.ai plus a local workstation running VS Code  
**Project Type**: Monorepo root operational tooling + documentation + agent command docs  
**Performance Goals**: First-time remote bootstrap to validated workspace in <=20 minutes excluding marketplace allocation time; reconnect or recovery to validated workspace in <=10 minutes; VS Code attach after setup in <=3 minutes  
**Constraints**: Keep changes in root-owned tooling and docs; preserve rerun safety; avoid direct imports from submodules; minimize manual copy/paste of SSH metadata; document unavoidable human steps explicitly; prefer canonical monorepo tools already in use  
**Scale/Scope**: Single developer or agent preparing one Vast.ai workspace at a time, with docs and commands sufficient for clean-machine setup, reconnect, and editor attach

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Ownership is explicit: planned changes stay in root-owned paths such as `tools/`, root README/operator docs, and `.opencode/commands/`; no backend or frontend repo code is touched.
- [x] Traceability is explicit: this feature does not depend on `retrieval` or `kmeans_segmentation` artifacts, so no producer/consumer contract boundary is crossed.
- [x] Reimplementation is explicit: no product behavior is derived from experiment code and no runtime imports from `fungal-cv-qdrant` are planned.
- [x] Canonical toolchains are explicit: shell orchestration remains in `tools/`, Python execution uses `uv`, shared tool installation uses `mise`, and any workflow verification uses `gh`.
- [x] Validation is explicit: shell validation, Python tests where relevant, documentation consistency review, manual Vast.ai bootstrap, reconnect, and VS Code attach are all named in Technical Context and Quickstart.
- [x] Definition of done is explicit: the touched surface requires local command validation, manual workstation-to-remote-to-editor verification, and updated operator plus agent documentation.
- [x] Contract sync is explicit: setup instructions, README/operator guidance, and `.opencode/commands/` will be updated together so human and agent workflows stay aligned.
- [x] Minimality is justified: the plan extends the existing root bootstrap surface instead of adding a new service, package, or cross-repo compatibility layer.

Post-design re-check: Pass. The research decisions, data model, contracts, and quickstart keep ownership at the monorepo root, preserve canonical toolchains, and require documentation plus manual validation evidence for the human and agent setup flow.

## Project Structure

### Documentation (this feature)

```text
specs/001-autonomous-vastai-setup/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── agent-vast-setup-command.md
│   └── workspace-bootstrap-cli.md
└── tasks.md
```

### Source Code (repository root)

```text
tools/
├── workspace_bootstrap.sh
├── dataset_sync.py
└── tests/

.opencode/
└── commands/

AGENTS.md
CLAUDE.md
README.md or root setup guide
```

**Structure Decision**: Root `tools/` owns executable workspace behavior, `.opencode/commands/` owns agent-facing setup prompts, and root/shared docs own human guidance. Existing `fungal-cv-qdrant` references may be updated only when they point to the shared remote-workspace flow, but no code ownership boundary changes.

## Complexity Tracking

No constitution exceptions or justified complexity violations are expected for this feature.
