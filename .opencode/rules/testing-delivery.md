# Rule: Testing and Delivery Strategy

The default MycoAI testing and delivery strategy is:

1. Classify the change first: experiment, backend, frontend, or shared-contract.
2. Write or update the smallest useful automated test in the owning repo.
3. Run the repo's local validation commands with the canonical toolchain.
4. If the change is user-facing, run a manual browser or API journey check.
5. If a relevant GitHub workflow exists, verify it with `gh` after local checks
   pass.
6. Only declare done when validation evidence, remaining risks, and contract
   impacts are ready for PR handoff.

Default expectations by context:

- Experiments: run the relevant `uv --directory fungal-cv-qdrant ...` command,
  validate logs or artifacts, and keep reports current.
- Backend: run `ruff check`, `ruff format --check`, `mypy`, and `pytest` via
  `uv --directory mycoai_retrieval_backend`.
- Frontend: run `lint`, `typecheck`, and `build` via
  `pnpm --dir mycoai_retrieval_frontend`; add unit or e2e coverage when
  behavior changes or explain why narrower validation is acceptable.
- Shared contracts: validate both producer and consumer repos and update docs in
  the same change.

Subagent responsibilities:

- `test-writer`: write focused unit or integration tests and minimal test-harness
  additions when justified.
- `test-runner`: run checks, collect outputs, and group failures by root cause.
- `e2e-writer`: author or update Playwright-style end-to-end coverage for user
  journeys.
- `manual-browser-tester`: exercise the final user path with browser or API
  checks and summarize the result.

Definition of done for autonomous delivery:

- The owning repo implementation is complete.
- Relevant local checks pass.
- Relevant workflow checks pass or the blocker is explicitly recorded.
- Manual validation is recorded for user-facing changes.
- PR-ready summary includes spec, plan, tasks, validation, contract impact, and
  residual risks.
