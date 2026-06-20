# Google Drive Data Sync Design

## Goal
Add monorepo-local `mise` tasks that set up an interactive Google Drive `rclone` remote using an existing Google Cloud OAuth client secret stored in `~/client_secret_2_996933128216-paplsqk16tipnjbor73p39bujeij29d6.apps.googleusercontent.com.json`, then sync `Dataset/`, `results/`, and `weights/` up or down between this repo and a dedicated Drive folder.

## Constraints
- Credentials must stay outside repo.
- Existing repo pattern already expects external `rclone` config via `RCLONE_CONFIG` or `~/.config/rclone/rclone.conf`.
- `mise` already manages `rclone` install in `mise.toml`.
- User wants simple sync entrypoints in `mise.toml` rather than deeper Python changes.
- Current machine can likely complete browser-based OAuth because it has active Wayland session and `xdg-open` available even though current shell is over SSH.

## Approaches

### 1. Add direct `rclone`-based `mise` tasks
Recommended.
- Add one auth task that creates/configures a Google Drive remote with client id and secret pulled from the existing JSON file.
- Add upload/download tasks that call `rclone sync` for `Dataset/`, `results/`, and `weights/`.
- Pros: small change set, standard `rclone` workflow, easy manual debugging, no new source files required.
- Cons: task commands are somewhat long and shell-heavy.

### 2. Add shell wrapper script plus `mise` tasks
- Move command logic to `tools/` shell script and keep `mise` tasks short.
- Pros: easier to read task entries.
- Cons: adds extra file for small workflow; user asked specifically for `mise.toml` script.

### 3. Extend `tools/dataset_sync.py`
- Teach existing Python sync CLI about `results/` and `weights/`, plus auth bootstrap.
- Pros: unified sync UX.
- Cons: broader scope than needed, mismatches current dataset-only design, more tests/docs churn.

## Recommendation
Use approach 1. Keep auth and sync orchestration in `mise.toml`, keep secrets/config external, and avoid touching Python sync code.

## Proposed Design

### Remote config
- Use remote name `mydrive` to match existing repo docs and dataset examples.
- Store `rclone` config at default `~/.config/rclone/rclone.conf` unless user later prefers `RCLONE_CONFIG`.
- Auth task parses `client_id` and `client_secret` from `~/client_secret_2_996933128216-paplsqk16tipnjbor73p39bujeij29d6.apps.googleusercontent.com.json`.
- Auth task runs `rclone config create mydrive drive ...` with browser-based OAuth enabled.
- Because `rclone config create` may still need token completion, task should end by printing `rclone lsd mydrive:` guidance or directly probing remote.

### Sync layout
- Use dedicated Drive folder root: `mydrive:mycoai-data`.
- Mirror these repo-root paths:
  - `Dataset/` ↔ `mydrive:mycoai-data/Dataset`
  - `results/` ↔ `mydrive:mycoai-data/results`
  - `weights/` ↔ `mydrive:mycoai-data/weights`
- Use `rclone sync` for exact mirror behavior because user asked for easy bidirectional syncing between machines, not additive copy-only behavior.
- Directional tasks:
  - `data-sync-down`: remote → local
  - `data-sync-up`: local → remote
- Keep per-directory sync as chained commands so failure stops later steps.

### Safety and UX
- Use `--progress` for visibility.
- Do not store secrets in repo or environment files.
- Auth task should create `~/.config/rclone/` if missing.
- Sync tasks should run from repo root and use `{{config_root}}`-style absolute paths avoided; instead hardcode repo-relative paths since `mise run` executes from project root.
- Prefer explicit remote env var inside task command (for example `MYCOAI_GDRIVE_REMOTE=${MYCOAI_GDRIVE_REMOTE:-mydrive:mycoai-data}`) so user can override folder without editing file.

### Files to change
- Modify `mise.toml` to add three tasks:
  - `gdrive-auth`
  - `data-sync-up`
  - `data-sync-down`
- Update `README.md` shared workspace tooling section with new `mise run ...` commands.
- Update `research/README.md` remote workspace section to mention same tasks from monorepo root.

### Validation
- Run `mise run gdrive-auth` manually to complete OAuth.
- Run `mise run data-sync-down` or `mise run data-sync-up` after auth.
- Verify remote visible with `mise x -- rclone lsd mydrive:`.
- No repo-specific lint/typecheck command directly covers TOML/README, so validate by reading edited files and exercising `mise` task parsing with `mise tasks ls`.
