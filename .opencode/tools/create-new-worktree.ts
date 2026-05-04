import { tool } from "@opencode-ai/plugin"
import { execSync } from "child_process"
import fs from "fs"
import path from "path"

type CommandResult = {
  ok: boolean
  command: string
  output: string
}

function runCommand(command: string, cwd: string): CommandResult {
  try {
    const output = execSync(command, {
      cwd,
      stdio: "pipe",
      encoding: "utf8",
    })
    return { ok: true, command, output: output.trim() }
  } catch (error) {
    const output = error instanceof Error ? error.message : String(error)
    return { ok: false, command, output: output.trim() }
  }
}

export default tool({
  description: "Create a project worktree and print init steps",
  args: {
    path: tool.schema.string().describe("Relative path for the new worktree"),
    branch: tool.schema.string().describe("Branch to create or use for the worktree"),
    base: tool.schema.string().optional().describe("Base ref for worktree branch").default("origin/main"),
  },
  async execute(args, context) {
    const repoRoot = context.worktree
    const worktreePath = path.resolve(repoRoot, args.path)
    const parentDir = path.dirname(worktreePath)

    if (!fs.existsSync(parentDir)) {
      return `Error: parent directory not found: ${parentDir}`
    }

    if (fs.existsSync(worktreePath)) {
      return `Error: worktree path already exists: ${worktreePath}`
    }

    const addResult = runCommand(
      `git worktree add -b "${args.branch}" "${worktreePath}" "${args.base}"`,
      repoRoot,
    )

    if (!addResult.ok) {
      return `Failed to create worktree\n${addResult.command}\n${addResult.output}`
    }

    return [
      `Created worktree: ${worktreePath}`,
      `Branch: ${args.branch}`,
      "Next run /init in the new worktree and follow this sequence:",
      "1. git submodule update --init --recursive",
      "2. git fetch origin",
      "3. if on main: git pull --ff-only origin main",
      "4. if repos/mycoai_retrieval_backend/.env.example exists: copy to .env",
      "5. if repos/mycoai_retrieval_frontend/.env.example exists: copy to .env",
      "6. uv --directory repos/mycoai_retrieval_backend sync --all-groups",
      "7. pnpm --dir repos/mycoai_retrieval_frontend install",
      "8. mise trust",
      "9. if .env.example exists: copy to .env and enter credentials manually",
    ].join("\n")
  },
})
