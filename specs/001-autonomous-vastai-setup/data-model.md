# Data Model: Autonomous Vast.ai Setup

## Overview

This feature improves operational setup and connection workflows rather than introducing an application database. The relevant entities describe the inputs, discovered remote state, validation results, and editor connection information needed for autonomous setup and recovery.

## Entity: Workspace Setup Profile

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `workspace_root` | path | Target monorepo root on the remote machine | Must resolve to the MycoAI monorepo root |
| `instance_id` | string | Vast.ai instance identifier used to rediscover the workspace | Optional for first setup, required for durable recovery |
| `ssh_key_ready` | boolean | Whether the required SSH identity is already available to the user and platform | Must be true before connection-dependent automation begins |
| `toolchain_ready` | boolean | Whether required local and remote tooling prerequisites are satisfied | Derived from prerequisite validation |
| `dataset_access_ready` | boolean | Whether optional external dataset access credentials are available | Required only for dataset sync workflows |
| `mode` | enum(`first_setup`, `recovery`) | Whether the workflow is provisioning or reconnecting | Must be explicit in output and guidance |
| `status` | enum(`pending`, `prepared`, `validated`, `blocked`) | Current workspace readiness state | Must follow the state transitions below |

### State Transitions

- `pending -> prepared`: workspace preparation finishes without fatal errors.
- `prepared -> validated`: smoke-check or equivalent validation passes.
- `pending | prepared -> blocked`: a missing prerequisite, failed lookup, or failed validation prevents safe continuation.
- `blocked -> prepared`: the missing requirement is resolved and setup is rerun successfully.

## Entity: Remote Instance Context

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `instance_id` | string | Stable Vast.ai handle for the rented machine | Must be non-empty for recovery flows |
| `ssh_host` | string | Current hostname or IP for SSH access | Must be non-empty when the instance is reachable |
| `ssh_port` | integer | SSH port for the active instance | Must be a valid TCP port |
| `ssh_user` | string | SSH username used to connect | Must be non-empty |
| `ssh_mode` | enum(`direct`, `proxy`, `unknown`) | How the machine is being accessed | Must reflect the current connection path |
| `workspace_root` | path | Remote path that should open in VS Code | Must point to the prepared monorepo root |
| `lifecycle_state` | enum(`discovered`, `running`, `replaced`, `unreachable`) | Current state of the remote machine from the workflow's perspective | Must match lookup or validation outcome |
| `last_seen_at` | timestamp | Last successful metadata or connectivity refresh | Optional until first lookup |

## Entity: Workspace Validation Result

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `phase` | enum(`prerequisites`, `prepare`, `smoke_check`, `recovery`, `editor_connect`) | Workflow phase that produced the result | Required |
| `status` | enum(`passed`, `failed`, `warning`) | Outcome of the phase | Required |
| `blocking_issues` | list[string] | Problems that must be fixed before continuing | Empty when status is `passed` |
| `next_actions` | list[string] | Clear follow-up steps for a human or agent | Must be present for warnings and failures |
| `evidence_location` | string | Command output, summary path, or copied descriptor proving the result | Optional but recommended for completed phases |

## Entity: Editor Connection Descriptor

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `host_alias` | string | Friendly alias suitable for local SSH or editor configuration | Must be non-empty if generated |
| `ssh_target` | string | Concrete SSH target the user or agent can invoke | Must be non-empty when connection is possible |
| `remote_path` | path | Folder that VS Code should open on the remote machine | Must equal the prepared workspace root |
| `descriptor_format` | enum(`ssh_config_snippet`, `ssh_command`, `vscode_instructions`) | How the connection information is represented | Must be explicit |
| `source` | enum(`provided`, `discovered`, `refreshed`) | Whether the details were supplied by the user or derived by the workflow | Required |

## Relationships

- One Workspace Setup Profile may reference one active Remote Instance Context.
- One Workspace Setup Profile may produce many Workspace Validation Results over time.
- One Remote Instance Context may produce one or more Editor Connection Descriptors as host details change.

## Validation Rules Derived from Requirements

- Setup and recovery must be rerun-safe and must not duplicate destructive initialization work by default.
- Connection information must be surfaced in a form directly useful for VS Code attachment.
- Validation output must distinguish between hard blockers and optional next steps.
- Manual steps must be reduced to unavoidable credential, rental, or first-time authorization actions and called out explicitly.
