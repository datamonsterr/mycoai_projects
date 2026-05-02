---
name: vast-ai-runner
description: Run canonical Vast.ai tasks from the local control plane, capture remote status, sync artifacts, and report cleanup state.
---

# Vast AI Runner

Use this when you need to execute a project command on a Vast.ai machine.

## Responsibilities

- use the one canonical repo-owned runner path
- keep the control plane local
- capture instance id, GPU, SSH details, command status, and artifact paths
- sync `Dataset/`, `results/`, and `weights/` through a configured rclone remote path such as `mydrive:mycoai-dataset`
