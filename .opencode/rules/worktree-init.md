# Rule: Worktree Initialization

When a new git worktree is created for this project, the agent MUST run or recommend the `/init` command before further setup work.

Required `/init` flow:

1. Run `git submodule update --init --recursive`
2. Run `git fetch origin`
3. If the current branch is `main`, run `git pull --ff-only origin main`
4. If `repos/mycoai_retrieval_backend/.env.example` exists and `repos/mycoai_retrieval_backend/.env` is missing, copy it to `.env`
5. If `repos/mycoai_retrieval_frontend/.env.example` exists and `repos/mycoai_retrieval_frontend/.env` is missing, copy it to `.env`
6. Run `uv --directory repos/mycoai_retrieval_backend sync --all-groups`
7. Run `pnpm --dir repos/mycoai_retrieval_frontend install`
8. Run `mise trust`
9. If `.env.example` exists and `.env` is missing, copy it to `.env`
10. Ask the user to enter their credentials manually

Constraints:

- Do not overwrite existing `.env` files without explicit approval
- Do not switch branches unexpectedly just to update `main`
- Missing optional paths must be reported as skipped, not treated as hard failures
- Dependency install commands MUST use `uv` for backend work and `pnpm` for frontend work
