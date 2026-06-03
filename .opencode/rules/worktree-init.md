# Rule: Worktree Initialization

When a new git worktree is created for this project, the agent MUST run or recommend the `/init` command before further setup work.

Required `/init` flow:

2. Run `git fetch origin`
3. If the current branch is `main`, run `git pull --ff-only origin main`
4. If `backend/.env.example` exists and `backend/.env` is missing, copy it to `.env`
5. If `frontend/.env.example` exists and `frontend/.env` is missing, copy it to `.env`
6. Run `uv --directory backend sync --all-groups`
7. Run `pnpm --dir frontend install`
8. Run `mise trust`
9. If `.env.example` exists and `.env` is missing, copy it to `.env`
10. Ask the user to enter their credentials manually

Constraints:

- Do not overwrite existing `.env` files without explicit approval
- Do not switch branches unexpectedly just to update `main`
- Missing optional paths must be reported as skipped, not treated as hard failures
- Dependency install commands MUST use `uv` for backend work and `pnpm` for frontend work
