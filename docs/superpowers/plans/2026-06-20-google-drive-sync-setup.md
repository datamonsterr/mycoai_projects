# Google Drive Sync Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `mise` tasks that configure `rclone` against Google Drive using existing external OAuth client secret and sync `Dataset/`, `results/`, and `weights/` between repo root and `mydrive:mycoai-data`.

**Architecture:** Keep Google Drive auth and sync orchestration in `mise.toml`, reuse external `rclone` config under `~/.config/rclone/rclone.conf`, and document the workflow in root README files. Avoid changing Python sync code because current request only needs repo-root data mirroring.

**Tech Stack:** mise, rclone, bash, TOML, Markdown

---

## File Structure

- Modify: `mise.toml` — add Google Drive auth and sync tasks.
- Modify: `README.md` — document `mise run gdrive-auth`, `mise run data-sync-up`, `mise run data-sync-down`.
- Modify: `research/README.md` — mention monorepo-root sync tasks in remote workspace docs.
- Reference only: `tools/dataset_sync.py` — existing dataset-only sync behavior stays unchanged.

### Task 1: Add Google Drive auth task to `mise.toml`

**Files:**
- Modify: `mise.toml`
- Reference: `/home/dat/client_secret_2_996933128216-paplsqk16tipnjbor73p39bujeij29d6.apps.googleusercontent.com.json`

- [ ] **Step 1: Add failing task definition mentally from current file structure**

Confirm new task belongs near existing workspace/data tooling in `mise.toml` and should not replace dataset sync tasks.

- [ ] **Step 2: Add auth task definition**

Add this block after existing dataset sync tasks:

```toml
[tasks.gdrive-auth]
description = "Create Google Drive rclone remote"
run = "python -c \"import json, pathlib; p = pathlib.Path.home() / 'client_secret_2_996933128216-paplsqk16tipnjbor73p39bujeij29d6.apps.googleusercontent.com.json'; data = json.loads(p.read_text())['installed']; print(data['client_id']); print(data['client_secret'])\" | { read -r CLIENT_ID; read -r CLIENT_SECRET; mkdir -p \"$HOME/.config/rclone\" && mise x -- rclone config create mydrive drive client_id \"$CLIENT_ID\" client_secret \"$CLIENT_SECRET\" scope drive root_folder_id '' && mise x -- rclone lsd mydrive:; }"
```

- [ ] **Step 3: Inspect task for shell correctness**

Check that:
- JSON path matches exact file name.
- `mkdir -p "$HOME/.config/rclone"` runs before `rclone` writes config.
- `mise x -- rclone ...` is used so PATH does not matter.
- remote name is `mydrive`.

- [ ] **Step 4: Run task listing to verify TOML parses**

Run: `mise tasks ls`
Expected: output includes `gdrive-auth`

- [ ] **Step 5: Commit**

```bash
git add mise.toml
git commit -m "feat: add Google Drive auth task"
```

### Task 2: Add directional sync tasks to `mise.toml`

**Files:**
- Modify: `mise.toml`

- [ ] **Step 1: Add down-sync task**

Add this block after `gdrive-auth`:

```toml
[tasks.data-sync-down]
description = "Sync Dataset results weights from Google Drive"
run = "MYCOAI_GDRIVE_REMOTE=${MYCOAI_GDRIVE_REMOTE:-mydrive:mycoai-data}; mise x -- rclone sync \"$MYCOAI_GDRIVE_REMOTE/Dataset\" Dataset --progress && mise x -- rclone sync \"$MYCOAI_GDRIVE_REMOTE/results\" results --progress && mise x -- rclone sync \"$MYCOAI_GDRIVE_REMOTE/weights\" weights --progress"
```

- [ ] **Step 2: Add up-sync task**

Add this block after `data-sync-down`:

```toml
[tasks.data-sync-up]
description = "Sync Dataset results weights to Google Drive"
run = "MYCOAI_GDRIVE_REMOTE=${MYCOAI_GDRIVE_REMOTE:-mydrive:mycoai-data}; mise x -- rclone sync Dataset \"$MYCOAI_GDRIVE_REMOTE/Dataset\" --progress && mise x -- rclone sync results \"$MYCOAI_GDRIVE_REMOTE/results\" --progress && mise x -- rclone sync weights \"$MYCOAI_GDRIVE_REMOTE/weights\" --progress"
```

- [ ] **Step 3: Run task listing to verify TOML parses**

Run: `mise tasks ls`
Expected: output includes `data-sync-down` and `data-sync-up`

- [ ] **Step 4: Dry-run command shape with help-level validation**

Run: `mise run data-sync-down --help`
Expected: mise recognizes task; if task execution semantics differ, fall back to `mise tasks ls` as parse validation only.

- [ ] **Step 5: Commit**

```bash
git add mise.toml
git commit -m "feat: add Google Drive sync tasks"
```

### Task 3: Document root workflow in `README.md`

**Files:**
- Modify: `README.md:138-148`

- [ ] **Step 1: Replace shared workspace tooling snippet**

Update snippet to include new `mise` commands while keeping existing workspace bootstrap and dataset sync examples:

```md
```bash
bash tools/workspace_bootstrap.sh prepare
bash tools/workspace_bootstrap.sh smoke-check
bash tools/workspace_bootstrap.sh recover --instance-id <vast-instance-id>

mise run gdrive-auth
mise run data-sync-down
mise run data-sync-up

uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py export --remote mydrive:mycoai-dataset --scope prepared/segments
```
```

- [ ] **Step 2: Add one explanatory sentence below snippet**

Add sentence:

```md
The `mise` Google Drive tasks mirror repo-root `Dataset/`, `results/`, and `weights/` through `mydrive:mycoai-data`; override the destination root with `MYCOAI_GDRIVE_REMOTE` when needed.
```

- [ ] **Step 3: Read updated section for style consistency**

Check wording matches concise command-first README style.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add Google Drive sync workflow"
```

### Task 4: Document remote-workspace workflow in `research/README.md`

**Files:**
- Modify: `research/README.md:88-99`

- [ ] **Step 1: Update preview and run dataset sync section**

Expand existing block to include monorepo-root `mise` sync tasks before dataset-specific CLI examples:

```md
```bash
mise run gdrive-auth
mise run data-sync-down
mise run data-sync-up

uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py import --remote mydrive:mycoai-dataset --scope curated_primary/sample
uv run python tools/dataset_sync.py export --remote mydrive:mycoai-dataset --scope prepared/segments
```
```

- [ ] **Step 2: Adjust explanatory paragraph**

Change paragraph to make clear that:
- `mise` tasks mirror repo-root data folders.
- dataset sync CLI remains non-destructive and dataset-scope-specific.
- both flows depend on external `rclone` credentials.

Use text like:

```md
The `mise` sync tasks mirror repo-root `Dataset/`, `results/`, and `weights/` directories through Google Drive, while the dataset sync CLI keeps its non-destructive `rclone copy` behavior for scoped dataset transfers. Both flows expect credentials to live outside the repo and write summaries under `results/dataset_sync/` when the dataset CLI runs from the monorepo root.
```

- [ ] **Step 3: Read updated section for consistency**

Check monorepo-root wording still matches surrounding remote-workspace guidance.

- [ ] **Step 4: Commit**

```bash
git add research/README.md
git commit -m "docs: describe monorepo Google Drive sync tasks"
```

### Task 5: Validate configuration and workflow

**Files:**
- Modify: `mise.toml`, `README.md`, `research/README.md`

- [ ] **Step 1: Verify task parsing**

Run: `mise tasks ls`
Expected: includes `gdrive-auth`, `data-sync-down`, `data-sync-up`

- [ ] **Step 2: Run repository validation command available for this area**

Run: `mise tasks ls | rg 'gdrive-auth|data-sync-down|data-sync-up'`
Expected: three matching lines

- [ ] **Step 3: Perform manual auth smoke check**

Run: `mise run gdrive-auth`
Expected: browser-based OAuth flow starts or remote already exists; final `rclone lsd mydrive:` succeeds.

- [ ] **Step 4: Perform non-destructive sync smoke check**

Run: `MYCOAI_GDRIVE_REMOTE=mydrive:mycoai-data mise x -- rclone lsd mydrive:mycoai-data`
Expected: remote path accessible.

- [ ] **Step 5: Read diff before final handoff**

Run: `git diff -- mise.toml README.md research/README.md`
Expected: only intended tasks/docs changes present.

- [ ] **Step 6: Commit**

```bash
git add mise.toml README.md research/README.md
git commit -m "feat: add Google Drive sync workflow"
```

## Self-Review

- Spec coverage checked: auth task, sync tasks, remote override, README docs, validation all covered.
- Placeholder scan checked: no TBD/TODO placeholders remain.
- Type and naming consistency checked: remote name `mydrive`, root `mydrive:mycoai-data`, task names `gdrive-auth`, `data-sync-down`, `data-sync-up` used consistently.
