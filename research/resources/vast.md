# Vast.ai Machine Reference

## Active machine

- Instance ID: `42862866`
- Public IP: `115.246.55.146`
- SSH port: `40345`
- Machine copy port: `40400`
- Public port range: `40296-40394`
- IP type: `Static`

## Open ports

- `115.246.55.146:40296 -> 1111/tcp`
- `115.246.55.146:40325 -> 6006/tcp`
- `115.246.55.146:40345 -> 22/tcp`
- `115.246.55.146:40354 -> 8080/tcp`
- `115.246.55.146:40383 -> 8384/tcp`
- `115.246.55.146:40394 -> 40394/tcp`

## Local addresses reported by Vast.ai

- `192.168.2.21`
- `192.168.122.1`
- `172.17.0.1`
- `2405:201:3051:a810:51fb:b6d1:1802:b6e5`
- `2405:201:3051:a810:c3ab:1bdd:fb7:5536`

## Canonical connection

SSH is already set up on this machine.

```bash
ssh -p 40345 <vast-user>@115.246.55.146
```

If user or host changes after restart, refresh details first:

```bash
vastai show instance 42862866
```

## Remote workspace rules

- Use `/workspace/mycoai` as repo root on Vast.ai.
- Use `/workspace/drive` as synced Drive staging root.
- `mydrive:mycoai-data` content synced to `/workspace/drive` on remote machine.
- Before using machine, check instance status with Vast CLI.
- After work finishes, terminate instance with Vast CLI. Start again only when needed.
- Fix code locally first, run smoke test locally until green, then sync code to remote machine and re-test there.
- After each run, copy `results/` and `weights/` outputs into Drive staging folders under `/workspace/drive`.
- Each results export folder must include datetime and experiment name.
- Cleanup remote machine after each run.

## Artifact staging layout

```text
/workspace/drive/
├── results/
│   └── <YYYYMMDD-HHMMSS>_<experiment-name>/
└── weights/
    └── <YYYYMMDD-HHMMSS>_<experiment-name>/
```

Example:

```text
/workspace/drive/results/20260627-153000_threshold/
/workspace/drive/weights/20260627-153000_threshold/
```

## Canonical workflow

Use `vast-ai-setup` skill for readiness and `vast-ai-runner` skill for execution.

1. Check machine status.
2. Start or confirm running instance.
3. Sync or copy latest code from local machine.
4. Run `bash tools/workspace_bootstrap.sh smoke-check` if workspace changed.
5. Run remote experiment or smoke test.
6. Copy `results/` and `weights/` artifacts into timestamped folders under `/workspace/drive`.
7. Remove temp files, stop unneeded services, clean workspace.
8. Terminate instance with Vast CLI.

## Vast CLI snippets

```bash
vastai show instance 42862866
vastai destroy instance 42862866
```
