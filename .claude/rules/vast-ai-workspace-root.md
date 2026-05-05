# Rule: Vast.ai Workspace Root

## Scope

This rule applies only when interacting with remote Vast.ai machines for this project.
It does not change local workstation paths.

## Required remote workspace path

Always use `/workspace/mycoai` as the monorepo root on Vast.ai machines.
Do not use `/root/mycoai`, `/workspace/mycoai_projects`, or other alternate roots unless the user explicitly overrides this rule.

## Required environment

Before running project commands on Vast.ai machines, set:

```bash
export MYCOAI_ROOT=/workspace/mycoai
```

This ensures repo code resolves shared paths correctly for:
- `Dataset/`
- `results/`
- `weights/`
- `species_weights.json`

## Canonical remote commands

```bash
cd /workspace/mycoai
bash tools/workspace_bootstrap.sh prepare --workspace-root /workspace/mycoai
bash tools/workspace_bootstrap.sh smoke-check --workspace-root /workspace/mycoai
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id> --workspace-root /workspace/mycoai
```

## Clone / move behavior

If repository is absent on Vast.ai machine, clone into:

```bash
/workspace/mycoai
```

If repository already exists under another remote path, prefer moving or re-cloning it into `/workspace/mycoai` before continuing.

## Long-running jobs

For heavy remote jobs, run from `/workspace/mycoai` and keep `MYCOAI_ROOT=/workspace/mycoai` set for the full session.
Prefer persistent session tools like `tmux` when appropriate.
