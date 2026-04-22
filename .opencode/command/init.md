---
description: Initialize or refresh a local checkout or newly created worktree for this project.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Prepare this project for either:

1. a new developer setting up the repo for the first time, or
2. a newly created git worktree that needs to be made usable.

## Required Flow

When running `/init`, perform these steps in order.

1. Verify the repo root contains `mise.toml`.
2. Initialize git submodules from the repo root.
   - Run: `git submodule update --init --recursive`
3. Refresh the current checkout from `origin/main`.
   - Run `git fetch origin`
   - Confirm the current branch/worktree state
   - If the current branch is `main`, run `git pull --ff-only origin main`
   - If the current branch is not `main`, update refs from `origin/main` and tell the user if they should rebase or merge manually instead of changing branches unexpectedly
4. Set up the admin UI workspace if `repos/nuoa-io-admin-ui/` exists.
   - If `repos/nuoa-io-admin-ui/.env.beta` exists and `.env` does not, copy `.env.beta` to `.env`
   - Run `yarn` in `repos/nuoa-io-admin-ui/`
   - If the path does not exist, report that it is skipped
5. Trust the project with mise.
   - Run: `mise trust`
6. Set up the root environment file.
   - If `.env.example` exists and `.env` does not, copy `.env.example` to `.env`
   - Then ask the user to open `.env` and enter their credentials or secrets manually
   - Never invent or write credentials

## Behavior Rules

- This command is intended for both fresh clones and fresh worktrees.
- Do not overwrite an existing `.env` file unless the user explicitly asks.
- Do not switch branches unexpectedly just to pull `main`.
- If local changes block a git operation, stop and report the exact blocker.
- If a required path is missing, skip it and report the skip clearly.
- Prefer repo-root execution unless a step explicitly targets a subdirectory.

## Suggested command sequence

Use the repo root unless noted otherwise:

```bash
git submodule update --init --recursive
git fetch origin
git branch --show-current
git pull --ff-only origin main
mise trust
cp .env.example .env
```

For the admin UI repo if present:

```bash
cp repos/nuoa-io-admin-ui/.env.beta repos/nuoa-io-admin-ui/.env
yarn
```

## Completion Report

At the end, report:

- submodule init status
- git refresh status
- admin UI env/yarn status
- mise trust status
- root `.env` status
- whether the user must add credentials manually
