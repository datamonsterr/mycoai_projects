# Skill: Speckit Worktrees Create

Use this skill when a feature workflow needs a dedicated git worktree before running Speckit commands.

## Workflow

1. Create the worktree on the requested branch
2. Open the new worktree root
3. Run the project `/init` command before `/speckit.specify`, `/speckit.plan`, or `/speckit.implement`

## Init requirements for this project

The `/init` command must perform this sequence:

1. `git submodule update --init --recursive`
2. `git fetch origin`
3. If current branch is `main`, `git pull --ff-only origin main`
4. If `mycoai_retrieval_backend/.env.example` exists and `mycoai_retrieval_backend/.env` is missing, copy it to `.env`
5. If `mycoai_retrieval_frontend/.env.example` exists and `mycoai_retrieval_frontend/.env` is missing, copy it to `.env`
6. Run `uv --directory mycoai_retrieval_backend sync --all-groups`
7. Run `pnpm --dir mycoai_retrieval_frontend install`
8. Run `mise trust`
9. If `.env.example` exists and `.env` is missing, copy it to `.env`
10. Prompt the user to enter credentials manually

## Notes

- Treat this flow as valid for both brand-new clones and fresh worktrees
- Skip missing optional paths and report them clearly
- Never auto-fill secrets
