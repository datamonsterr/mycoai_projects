import type { Plugin } from "@opencode-ai/plugin"
import fs from "fs"
import path from "path"

export const AutolabCompactionPlugin: Plugin = async (ctx) => {
  return {
    "experimental.session.compacting": async (input, output) => {
      const root = ctx.worktree
      const contextChunks: string[] = []

      const resultstsv = path.join(root, "repos/fungal-cv-qdrant/research/results.tsv")
      if (fs.existsSync(resultstsv)) {
        const rows = fs.readFileSync(resultstsv, "utf-8").trim().split("\n").slice(-5)
        contextChunks.push(`## Last 5 experiment runs (results.tsv)\n${rows.join("\n")}`)
      }

      const paperIdeas = path.join(root, "repos/fungal-cv-qdrant/research/paper-ideas.md")
      if (fs.existsSync(paperIdeas)) {
        const content = fs.readFileSync(paperIdeas, "utf-8")
        const pending = content.match(/## Paper:.*?\n[\s\S]*?Status\*\*: pending/g) ?? []
        const inProgress = content.match(/## Paper:.*?\n[\s\S]*?Status\*\*: in-progress/g) ?? []
        contextChunks.push(
          `## Research queue\nPending: ${pending.length} | In-progress: ${inProgress.length}`,
        )
      }

      const worktreeOut = (() => {
        try {
          const { execSync } = require("child_process")
          return execSync("git -C repos/fungal-cv-qdrant worktree list", {
            cwd: root,
            encoding: "utf-8",
          }).trim()
        } catch {
          return "unavailable"
        }
      })()
      contextChunks.push(`## Active worktrees\n${worktreeOut}`)

      output.context.push(`## Autolab Session State\n\n${contextChunks.join("\n\n")}`)
    },
  }
}
