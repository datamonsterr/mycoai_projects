# Phase 0 Research: Vast.ai Workspace Bootstrap and Dataset Sync

## Decision 1: Use VSCode Remote-SSH over Vast.ai SSH as the primary editor path

- **Decision**: Standardize on local VSCode `Remote - SSH` as the canonical
  editor workflow. Prefer direct SSH offers on Vast.ai when available and fall
  back to proxy SSH when necessary. Treat the Vast.ai `instance_id` as the
  source of truth for reconnecting after host or port changes.
- **Rationale**: The user explicitly wants VSCode, and Remote-SSH is the
  shortest path from a fresh rented machine to a working remote workspace. It
  avoids adding another exposed service, matches Vast.ai's native SSH-centric
  access model, and keeps recovery centered on rediscovering connection info
  rather than preserving static IP assumptions.
- **Alternatives considered**:
  - Browser-based Jupyter or portal access: acceptable as emergency access but
    not a substitute for local VSCode.
  - `code-server` or similar browser IDE: rejected because it adds another
    service to expose, secure, and recover.
  - VS Code tunnels or custom agents: rejected because they add setup overhead
    and are slower than plain SSH for this use case.

## Decision 2: Keep shared setup and sync tooling at monorepo root `tools/`

- **Decision**: Implement the feature as new root-level tools under
  `/home/dat/dev/mycoai/tools/`, with shell used for workspace/bootstrap
  orchestration and Python used for dataset sync planning, guardrails, and
  reporting.
- **Rationale**: The feature operates on root-level assets such as `Dataset/`,
  `mise.toml`, and shared workspace conventions. Keeping it in
  `fungal-cv-qdrant/tools/` would put shared-path logic in the wrong ownership
  boundary. A mixed shell and Python design is the smallest safe change because
  machine bootstrap is mostly command orchestration, while transfer planning and
  validation benefit from structured Python logic.
- **Alternatives considered**:
  - Keep tools in `fungal-cv-qdrant/tools/`: rejected because the user
    explicitly wants monorepo-level tools and the feature targets root paths.
  - Put tools in `.opencode/tools/`: rejected because that area is agent
    infrastructure, not user-facing project tooling.
  - Use all shell: rejected because direction checks, scope validation, and
    transfer summaries are easier to make safe in Python.
  - Use all Python: rejected because remote bootstrap still needs shell-oriented
    orchestration of SSH, git, and host tools.

## Decision 3: Use `rclone` with copy-first semantics for Google Drive sync

- **Decision**: Use `rclone` with a dedicated Google Drive remote rooted to a
  specific dataset folder. Implement default import and export flows with
  `copy` semantics, and require a preview step before execution. Do not expose a
  destructive mirror mode in the initial version.
- **Rationale**: `rclone` is reliable on headless Linux machines, supports
  Google Drive well, and provides dry-runs, scoped transfers, logging, and
  summaries. `copy` avoids accidental deletion at the destination while still
  supporting incremental import and export. This aligns with the feature's need
  for explicit transfer direction and safe proof-of-access checks.
- **Alternatives considered**:
  - Google Drive mount tools: rejected because they are less stable and less
    predictable for scripted remote GPU workflows.
  - Lightweight Drive CLIs: rejected because they offer weaker filtering,
    reporting, and safety semantics than `rclone`.
  - Custom Drive API integration: rejected because it adds maintenance and
    credential surface without clear benefit over `rclone`.

## Decision 4: Keep credentials outside the repo and support scoped proof-of-access

- **Decision**: Treat Google Drive access material as external secrets, not repo
  files. The sync workflow will support proof-of-access via listing and dry-run
  previews before a real transfer, with folder-scoped selection rather than
  assuming full `Dataset/` movement on every run.
- **Rationale**: Remote GPU instances are ephemeral, and the repo must not
  become a home for user tokens or machine-specific secrets. Scoped previews are
  the simplest way to protect users from large accidental transfers and confirm
  that a rented instance has correct Drive access before waiting on a full sync.
- **Alternatives considered**:
  - Store credentials in the repo or under `Dataset/`: rejected as unsafe and
    incompatible with the monorepo boundary rules.
  - Full-dataset-only syncs: rejected because they are too slow and risky for
    a first validation step on a fresh machine.

## Decision 5: Design for disposable instances and fast recovery

- **Decision**: Assume Vast.ai instances are disposable. The implementation will
  optimize for fast rebuild and reconnection instead of treating instance-local
  state as durable. Recovery will be based on re-querying connection details,
  rerunning smoke validation, and restoring data from Git plus the Drive mirror.
- **Rationale**: Vast.ai instances can change host, port, or disappear entirely.
  A recovery model centered on reproducible bootstrap and externalized dataset
  state is more reliable than trying to preserve every machine-local detail.
- **Alternatives considered**:
  - Treat stopped instances as stable long-lived workstations: rejected because
    it creates brittle assumptions about IPs, ports, and local storage.
  - Depend on manual tribal knowledge for recovery: rejected because the feature
    explicitly needs repeatability and speed.
