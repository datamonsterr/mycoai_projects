# Skill: Using Git Worktrees

Use this skill when a user wants to create, refresh, or work inside a git worktree for this project.

## Project-specific worktree flow

After creating or opening a new worktree, run the repo init flow.

1. From the worktree root, run `git submodule update --init --recursive`
2. Run `git fetch origin`
3. If the current branch is `main`, run `git pull --ff-only origin main`
4. If `mycoai_retrieval_backend/.env.example` exists and `mycoai_retrieval_backend/.env` does not, copy it to `.env`
5. If `mycoai_retrieval_frontend/.env.example` exists and `mycoai_retrieval_frontend/.env` does not, copy it to `.env`
6. Run `uv --directory mycoai_retrieval_backend sync --all-groups`
7. Run `pnpm --dir mycoai_retrieval_frontend install`
8. Run `mise trust`
9. If `.env.example` exists and `.env` does not, copy it to `.env`
10. Ask the user to fill in credentials manually in any created `.env` files

## Safety rules

- Do not overwrite existing `.env` files unless the user requests it
- Do not switch branches unexpectedly in an existing worktree
- If a path such as `mycoai_retrieval_backend/` or `mycoai_retrieval_frontend/` is missing, skip it and report the skip
- If local changes block fetch or pull flows, stop and report the blocker

## Recommended helper

If available, use `.opencode/tools/create-new-worktree.ts` to create the worktree, then run `/init` inside the new worktree.
