# Vast.ai Run Rule

Context: Vast.ai remote execution for MycoAI research.
Source of truth: `research/resources/vast.md`.

Correct rule:
1. Read `research/resources/vast.md` before any Vast.ai action.
2. Use `vast-ai-setup` skill for readiness checks and `vast-ai-runner` skill for execution.
3. Check Vast.ai machine status with `vastai show instance 42862866` before use.
4. Use Vast CLI workflow for lifecycle control; terminate instance after work, restart only when needed.
5. Use remote repo root `/workspace/mycoai` and Drive staging root `/workspace/drive`.
6. Treat `mydrive:mycoai-data` as remote sync source/destination mounted or synced through `/workspace/drive`.
7. Fix code locally first, run smoke test locally until pass, then sync code to machine and test remotely.
8. After each run, copy `results/` and `weights/` into `/workspace/drive` under folders named `<YYYYMMDD-HHMMSS>_<experiment-name>`.
9. Cleanup remote machine after each run.

Active machine:
- Instance ID: `42862866`
- Public IP: `115.246.55.146`
- SSH port: `40345`
- Machine copy port: `40400`
- Open service ports: `40296`, `40325`, `40354`, `40383`, `40394`
