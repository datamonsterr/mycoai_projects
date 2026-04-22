# Quickstart: Autonomous Vast.ai Setup

## Goal

Go from a local workstation with the required credentials to a validated MycoAI workspace on Vast.ai, then open that workspace in VS Code with as little manual handling as possible.

## Prerequisites

1. A Vast.ai account with an attached SSH key.
2. A local machine with SSH and VS Code plus the Remote-SSH capability.
3. Access to this MycoAI monorepo and its submodules.
4. Required external credentials available outside the repo, including any dataset-sync credentials if dataset transfer is part of the session.
5. Optional Vast.ai CLI access if you want connection metadata to be refreshed from the command line instead of the web UI.

## 1. Acquire or identify the remote machine

1. Rent or reuse a Vast.ai instance that supports SSH access.
2. Record the `instance_id` as the durable recovery handle.
3. Obtain the current SSH host, port, and user details from the platform or CLI.

## 2. Access the machine and prepare the workspace

1. Connect to the remote machine over SSH.
2. Clone or open the MycoAI monorepo on the remote machine.
3. From the monorepo root, run:

```bash
bash tools/workspace_bootstrap.sh prepare --non-interactive
```

4. Review the resulting workspace summary and retain any printed connection or recovery details.

## 3. Validate readiness

Run:

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

The workspace is ready only when the smoke-check completes successfully and no blocking prerequisite issues remain.

## 4. Open the workspace from VS Code

1. Use the surfaced SSH details or generated connection descriptor.
2. Open the remote host with VS Code Remote-SSH.
3. Open the prepared monorepo root folder on the remote machine.
4. Confirm that file browsing and an integrated terminal work.

## 5. Recover after restart, reconnect, or replacement

If the machine changes host or port, rediscover the latest SSH details from the saved `instance_id`, reconnect, and run:

```bash
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>
```

If host or port changed and is already known, include the refreshed values in the recovery call so the workflow can echo the updated connection state.

## 6. Declare setup complete

Setup is complete only when all of the following are true:

- prepare finished without blocking errors
- smoke-check passed
- the current instance details are recorded
- VS Code opened the correct remote workspace
- any remaining manual steps are documented as external platform requirements rather than unresolved setup gaps
