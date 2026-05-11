# Living Specs

Auto-synced copies of `feature_spec/`. Do not edit files here directly.

## What Are Living Specs?

Living specs are working copies of the ground-truth feature specifications.
They are automatically synced from `docs/feature_spec/` by the spec-syncer
subagent.

## Why Two Folders?

| Folder | Purpose |
|--------|---------|
| `docs/feature_spec/` | Ground truth. Humans and agents edit these directly. |
| `docs/living_spec/` | Auto-synced copies. Agents read these during implementation to ensure they always have the latest version. |

## Workflow

1. Human or agent edits `docs/feature_spec/*.md`
2. Run spec-syncer: copies to `docs/living_spec/`, updates metadata
3. Implementation agents pull `docs/living_spec/` for current context

## Metadata

Each living spec file has a header comment tracking sync date and version:

    <!-- synced: 2025-05-11T14:30:00Z from feature_spec/01-image-input.md -->

## Commands

```bash
# Sync feature_spec -> living_spec
# (invoke spec-syncer subagent)

# Pull living spec for current work context
# (invoke spec-puller subagent)
```
