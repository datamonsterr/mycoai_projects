# Data Model: Vast.ai Workspace Bootstrap and Dataset Sync

## Overview

This feature introduces monorepo-level operational tooling rather than a new
application database. The relevant entities are operator-facing records used to
model remote workspace readiness and dataset transfer behavior.

## Entity: Workspace Profile

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `instance_id` | string | Vast.ai instance identifier used as the durable reconnect handle | Required for any recovery flow that queries current connection info |
| `ssh_mode` | enum(`direct`, `proxy`) | Preferred connection method for the instance | Must be one of the supported SSH modes |
| `ssh_host` | string | Current resolved host for the instance | Must be non-empty when connection details are known |
| `ssh_port` | integer | Current SSH port | Must be a valid TCP port |
| `ssh_user` | string | Remote login user | Must be non-empty |
| `workspace_root` | path | Absolute path to the monorepo on the remote machine | Must resolve to the MycoAI monorepo root |
| `dataset_root` | path | Absolute path to the root `Dataset/` directory | Must equal `workspace_root/Dataset` unless explicitly overridden by shared root conventions |
| `status` | enum(`discovered`, `bootstrapped`, `validated`, `recovery_needed`) | Current readiness of the remote workspace | Transitions must follow the state model below |
| `last_verified_at` | timestamp | Last successful smoke-check time | Optional until first validation |

### Relationships

- One Workspace Profile can use one Dataset Mirror.
- One Workspace Profile can have many Dataset Sync Sessions over time.

### State Transitions

- `discovered -> bootstrapped`: remote setup has created the expected repo and
  tooling layout.
- `bootstrapped -> validated`: smoke validation has passed.
- `validated -> recovery_needed`: instance restart, address change, or failed
  smoke check requires operator action.
- `recovery_needed -> validated`: recovery flow has completed and smoke
  validation passes again.

## Entity: Dataset Mirror

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `remote_name` | string | Logical name of the Google Drive remote | Must reference a configured external credential source |
| `remote_root` | string | Drive path or dedicated root folder for MycoAI dataset exchange | Must be non-empty and must not point to an unrestricted personal root |
| `local_root` | path | Local dataset directory in the monorepo | Must resolve to the root `Dataset/` directory |
| `default_direction` | enum(`import`, `export`) | Operator-selected intent for a transfer | Must be explicit for each real transfer |
| `supports_scoped_transfer` | boolean | Whether folder or pattern-scoped transfer is enabled | Must be `true` for the initial release |

### Relationships

- One Dataset Mirror belongs to one Workspace Profile.
- One Dataset Mirror can have many Dataset Sync Sessions.

## Entity: Dataset Sync Session

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `session_id` | string | Unique identifier for a single transfer attempt | Required |
| `direction` | enum(`import`, `export`) | Transfer direction relative to local `Dataset/` | Required and must be explicit |
| `scope` | list[string] | Selected subfolders, include patterns, or file list references | Can be empty only when the full dataset scope is intended |
| `preview_only` | boolean | Whether this is a proof-of-access or dry-run preview | Required |
| `status` | enum(`planned`, `previewed`, `executed`, `failed`) | Current transfer state | Must follow the state model below |
| `transferred_count` | integer | Number of transferred items | Must be `0` for preview-only runs |
| `skipped_count` | integer | Number of skipped items | Non-negative |
| `failed_count` | integer | Number of failed items | Non-negative |
| `summary_path` | path | Path to the transfer summary or log output | Must be recorded for executed runs |
| `started_at` | timestamp | Start time for the transfer | Required |
| `finished_at` | timestamp | Finish time for the transfer | Optional until completion |

### State Transitions

- `planned -> previewed`: a scoped preview or dry-run completes successfully.
- `previewed -> executed`: the operator confirms the real transfer.
- `planned -> executed`: allowed for deliberate full transfers when preview is
  skipped by policy exception, but not the default path.
- `planned | previewed | executed -> failed`: any credential, storage, or
  network error blocks completion.

## Validation Rules Derived from Requirements

- Local data movement must always target the monorepo root `Dataset/` path.
- Every transfer must make direction explicit before data movement begins.
- The initial implementation must support scoped or sample transfers.
- The initial implementation must produce a human-readable transfer summary.
- Credentials must live outside the repo and outside `Dataset/`.
