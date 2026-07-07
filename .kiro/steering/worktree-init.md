---
inclusion: manual
---

# Worktree Initialization

When a new git worktree is created, run this init flow:

1. `git fetch origin`
2. If on `main`: `git pull --ff-only origin main`
3. If `backend/.env.example` exists and `backend/.env` missing: copy it
4. If `frontend/.env.example` exists and `frontend/.env` missing: copy it
5. `uv --directory backend sync --all-groups`
6. `pnpm --dir frontend install`
7. `mise trust`
8. If root `.env.example` exists and `.env` missing: copy it
9. Ask user to enter credentials manually

## Constraints

- Do NOT overwrite existing `.env` files without approval
- Do NOT switch branches unexpectedly
- Missing optional paths → report as skipped, not hard failure
- Use `uv` for backend, `pnpm` for frontend
