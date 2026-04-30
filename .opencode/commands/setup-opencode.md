---
description: Interactive setup for your local OpenCode model and TUI configuration
---

You are helping the developer configure their local OpenCode for this MycoAI project.

## What this does

Writes two files (does NOT touch shared project config):
- `~/.config/opencode/opencode.json` — your model and provider preferences
- `~/.config/opencode/tui.json` — your TUI preferences

Also verifies the project GitHub CLI profile:
- MyCoAI uses `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr"`
- The profile must be authenticated as `datamonsterr`
- Agents must run `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh <args>` and must not run `gh auth switch`

Since the project config (`.opencode/opencode.json`) does NOT set any models, your global config takes full effect.

## Config precedence reference

```
6 (highest)  OPENCODE_CONFIG_CONTENT  env var — runtime overrides
5            OPENCODE_CONFIG           env var — custom config file path
4            Project config            .opencode/opencode.json (agent paths, MCP, tools — NO models)
3            Global config             ~/.config/opencode/opencode.json ← YOUR MODELS GO HERE
2            Global TUI                ~/.config/opencode/tui.json
1 (lowest)   Remote config             .well-known/opencode — organizational defaults
```

## Step 1: Verify GitHub CLI profile

Run `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh auth status -h github.com`.
If not authenticated as `datamonsterr`, ask the developer to run `GH_CONFIG_DIR="$HOME/.config/gh-datamonsterr" gh auth login -h github.com`.
Never use `gh auth switch`.

## Step 2: Check available models

Run `opencode models` to list all available models.
Show the output so the developer can pick valid models.

## Step 3: Ask for 2 model choices

OpenCode uses just **2 top-level model settings**:

### `model` (default)
Primary model for all agents and conversations.
Example: `opencode-go/glm-5.1`, `anthropic/claude-sonnet-4-5`

### `small_model`
Fast/cheap model for lightweight tasks (explore, general, setup, etc.).
Example: `opencode-go/minimax-m2.7`, `anthropic/claude-haiku-4-5`

Suggest these defaults if available on the developer's system:
- `model` → `opencode-go/glm-5.1`
- `small_model` → `opencode-go/minimax-m2.7`

## Step 4: Write opencode.json

Write `~/.config/opencode/opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "<MODEL>",
  "small_model": "<SMALL_MODEL>"
}
```

**Optional:** If the developer uses a specific provider, also set the `provider` block. For example:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5",
  "small_model": "anthropic/claude-haiku-4-5",
  "provider": {
    "anthropic": {
      "disabled": false
    }
  }
}
```

Only include the `provider` block if the developer requests it.

**Optional:** If the developer wants to override specific agents with different models, add an `agent` block:

```json
{
  "model": "opencode-go/glm-5.1",
  "small_model": "opencode-go/minimax-m2.7",
  "agent": {
    "superagent": { "model": "anthropic/claude-sonnet-4-5" }
  }
}
```

Only add agent overrides if the developer explicitly requests them.

## Step 5: Ask about TUI preferences

Ask if they want to customize TUI settings. If no, skip to Step 6.

If yes, ask:
- **Theme:** `"opencode"` (default) or `"tokyonight"`
- **Scroll speed:** default `3`
- **Diff style:** `"auto"` (default, adapts to width) or `"stacked"` (single column)

Write `~/.config/opencode/tui.json`:

```json
{
  "$schema": "https://opencode.ai/tui.json",
  "theme": "opencode",
  "scroll_speed": 3,
  "scroll_acceleration": { "enabled": true },
  "diff_style": "auto"
}
```

## Step 6: Confirm and next steps

Show the final configs and confirm. Then provide:

- `opencode` — start using the new config
- `opencode models` — see available models anytime
- `opencode models <provider>` — filter by provider
- Edit `~/.config/opencode/opencode.json` to change models later
- Edit `~/.config/opencode/tui.json` to change TUI settings later
- `opencode --model <provider/model-id>` — override model for one session