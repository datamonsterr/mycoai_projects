---
inclusion: manual
---

# Vast.ai Remote Workspace

## Workspace Root

Always use `/workspace/mycoai` as the monorepo root on Vast.ai machines.

```bash
export MYCOAI_ROOT=/workspace/mycoai
```

## Canonical Commands

```bash
cd /workspace/mycoai
bash tools/workspace_bootstrap.sh prepare --workspace-root /workspace/mycoai
bash tools/workspace_bootstrap.sh smoke-check --workspace-root /workspace/mycoai
bash tools/workspace_bootstrap.sh recover --instance-id <id> --workspace-root /workspace/mycoai
```

## Rules

- If repo absent on Vast.ai, clone into `/workspace/mycoai`
- If repo exists elsewhere, move/re-clone to `/workspace/mycoai`
- For long-running jobs, keep `MYCOAI_ROOT=/workspace/mycoai` set for full session
- Use `tmux` for persistent sessions
