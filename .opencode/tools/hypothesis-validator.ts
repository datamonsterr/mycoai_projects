import { tool } from "@opencode-ai/plugin"
import fs from "fs"
import path from "path"

export default tool({
  description:
    "Validate a proposed hypothesis: check for duplicates in paper-ideas.md and do-not-repeat.md, and assess fit against experiment programs. Returns VALID, DUPLICATE, or REJECTED with reason.",
  args: {
    experiment: tool.schema.string().describe("Target experiment name, e.g. 'retrieval'"),
    strategy: tool.schema
      .string()
      .describe("Short strategy description to check for duplicates"),
    proposed_strategy: tool.schema
      .string()
      .optional()
      .describe("Full proposed strategy text (for semantic duplicate check)"),
  },
  async execute(args, context) {
    const root = context.worktree
    const paperIdeasPath = path.join(
      root,
      "repos/fungal-cv-qdrant/research/paper-ideas.md",
    )
    const doNotRepeatPath = path.join(
      root,
      "repos/fungal-cv-qdrant/research/do-not-repeat.md",
    )
    const programPath = path.join(
      root,
      "repos/fungal-cv-qdrant/src/experiments",
      args.experiment,
      "program.md",
    )

    const results: string[] = []

    const normalize = (s: string) => s.toLowerCase().replace(/\s+/g, " ").trim()
    const strategyNorm = normalize(args.strategy)

    if (fs.existsSync(doNotRepeatPath)) {
      const doNotRepeat = fs.readFileSync(doNotRepeatPath, "utf-8")
      const lines = doNotRepeat.split("\n")
      for (const line of lines) {
        if (line.includes(args.strategy) || normalize(line).includes(strategyNorm)) {
          return `REJECTED: Strategy already in do-not-repeat.md\nMatched line: ${line.trim()}`
        }
      }
    }

    if (fs.existsSync(paperIdeasPath)) {
      const ideas = fs.readFileSync(paperIdeasPath, "utf-8")
      const blocks = ideas.split(/^## Paper:/m).slice(1)
      const matchedBlock = blocks.find((block) => {
        const normalizedBlock = normalize(block)
        return (
          normalizedBlock.includes(strategyNorm) ||
          (args.proposed_strategy &&
            normalizedBlock.includes(normalize(args.proposed_strategy).slice(0, 40)))
        )
      })
      if (matchedBlock) {
        const statusMatch = matchedBlock.match(/\*\*Status\*\*:\s*([^\n]+)/)
        const status = normalize(statusMatch?.[1] ?? "pending")
        if (status === "in-progress" || status === "completed") {
          return `DUPLICATE: Strategy already ${status} in paper-ideas.md\nStrategy: ${args.strategy}`
        }
        return `DUPLICATE: Strategy already ${status} in paper-ideas.md — skip or modify\nStrategy: ${args.strategy}`
      }
    }

    if (!fs.existsSync(programPath)) {
      results.push(
        `WARNING: No program.md found at src/experiments/${args.experiment}/ — experiment may not exist`,
      )
    } else {
      const program = fs.readFileSync(programPath, "utf-8")
      results.push(`FIT CHECK: program.md exists for '${args.experiment}'`)
      if (program.toLowerCase().includes("retrieval") && args.experiment !== "retrieval") {
        results.push("INFO: program.md mentions retrieval but experiment name differs")
      }
    }

    results.unshift(`VALID: No duplicates found for strategy: "${args.strategy}"`)
    return results.join("\n")
  },
})
