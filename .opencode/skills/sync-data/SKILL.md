---
name: sync-data
description: Configure Google Drive / rclone shared storage and run non-destructive sync for Dataset, results, and weights.
---

# Sync Data

Use this when you need to set up or run shared storage sync.

## Responsibilities

- reuse `tools/dataset_sync.py`
- validate `rclone` and credential state
- support `Dataset/`, `results/`, and `weights/` scopes
- use a configured rclone remote root such as `mydrive:mycoai-dataset`
