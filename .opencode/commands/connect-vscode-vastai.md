---
description: Generate or use a VS Code Remote-SSH connection descriptor from current Vast.ai SSH metadata
---

You are helping connect VS Code to a prepared MycoAI workspace on a Vast.ai
remote machine. The canonical entrypoint is `tools/workspace_bootstrap.sh`.

## Quick Connect (when instance details are known)

If the SSH host, user, and port are already known:

```bash
bash tools/workspace_bootstrap.sh prepare \
  --ssh-host <host> --ssh-user <user> --ssh-port <port> \
  --non-interactive
```

This prints a connection descriptor section in the output. Use that to attach
VS Code.

## Connection Descriptor Format

The script produces output in this format:

```
Connection descriptor (VS Code Remote-SSH)
  ssh_target:   user@host -p port
  remote_path:  /path/to/monorepo/root
  instance_id:  <vast-instance-id>
  source:       provided

  VS Code Remote-SSH steps:
    1. Open VS Code Command Palette (Ctrl+Shift+P)
    2. Run: Remote-SSH: Connect to Host...
    3. Enter: ssh user@host -p port
    4. Open folder: /path/to/monorepo/root
    5. Verify file browsing and integrated terminal work
```

## Using the Descriptor

### Direct SSH Command

Copy the `ssh_target` line and paste it into the VS Code Remote-SSH "Connect to
Host..." dialog.

### Manual SSH Config Entry

To add to `~/.ssh/config` for persistent access:

```
Host mycoai-vast
    HostName <host>
    User <user>
    Port <port>
    IdentityFile ~/.ssh/id_rsa
```

Then in VS Code Remote-SSH: "Connect to Host..." → select `mycoai-vast`.

## Verifying the Connection

After connecting, verify:

1. **File browsing**: Open the remote workspace root folder. You should see
   `Dataset/`, `results/`, `weights/`, `repos/`, `tools/`.
2. **Integrated terminal**: Run `pwd` — should show the workspace root.
3. **Smoke validation** (optional but recommended):

```bash
bash tools/workspace_bootstrap.sh smoke-check
```

## Reconnecting After Instance Changes

If the Vast.ai instance restarted (host or port changed):

1. Rediscover the new SSH details from Vast.ai UI or CLI:

```bash
vastai show instance <instance-id>
```

2. Re-run the workspace recovery:

```bash
bash tools/workspace_bootstrap.sh recover \
  --instance-id <instance-id> \
  --host <new-host> --port <new-port>
```

3. Use the updated connection descriptor to reconnect VS Code.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| "Host key verification failed" | Accept the host key: `ssh-keyscan -p <port> <host> >> ~/.ssh/known_hosts` or connect once from terminal first |
| "Connection refused" | Verify instance is running and SSH port is correct in Vast.ai UI |
| VS Code shows wrong workspace | Use "Open Folder..." and navigate to the correct monorepo root path |
| "Permission denied (publickey)" | Verify SSH key is attached in Vast.ai account and key file path is correct in `~/.ssh/config` |
| Remote terminal not working | Run `bash tools/workspace_bootstrap.sh smoke-check` to verify workspace state |
