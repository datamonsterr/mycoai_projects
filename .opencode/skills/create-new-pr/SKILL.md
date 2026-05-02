---
name: create-new-pr
description: Create a PR for the monorepo root or a submodule by collecting commit history, diff from main, and spec/plan/task context. Include related PR links between main repo and submodule PRs.
---

# Create New PR

Use this when you need a PR for the monorepo root or one submodule.

## Responsibilities

- inspect git status, branch tracking, commit history, and base diff
- read related spec, plan, tasks, contracts, and validation evidence
- draft a concise PR title and body
- create the PR with `GH_CONFIG_DIR=\"$HOME/.config/gh-datamonsterr\" gh pr create` when asked
- never use `gh auth switch`
- cross-link main-repo and submodule PRs

## Required PR Body Sections

- Summary
- Specs / Plan / Tasks
- Validation
- Contract Impact
- Related PRs

## Submodule Linking Rule

- each submodule spec PR must link to the related main-repo PR
- each main-repo PR that updates submodule pointers must link to the related submodule PRs
