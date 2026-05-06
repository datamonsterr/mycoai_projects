import { tool } from "@opencode-ai/plugin"
import { execSync } from "child_process"

export default tool({
  description:
    "Run experiment package validation checks (ruff, mypy, pytest) for one or more experiment packages inside repos/fungal-cv-qdrant. Returns pass/fail summary grouped by check type.",
  args: {
    experiments: tool.schema
      .array(tool.schema.string())
      .describe("List of experiment names to check, e.g. ['retrieval', 'threshold']"),
    checks: tool.schema
      .array(tool.schema.enum(["ruff", "mypy", "pytest", "import"]))
      .optional()
      .default(["ruff", "mypy", "import"])
      .describe("Which checks to run"),
  },
  async execute(args, context) {
    const cwd = `${context.worktree}/repos/fungal-cv-qdrant`
    const lines: string[] = []

    function run(cmd: string): { ok: boolean; output: string } {
      try {
        const output = execSync(cmd, { cwd, stdio: "pipe", encoding: "utf8" })
        return { ok: true, output: output.trim() }
      } catch (e: unknown) {
        const err = e as { stdout?: string; stderr?: string; message?: string }
        const output = [err.stdout, err.stderr, err.message].filter(Boolean).join("\n")
        return { ok: false, output: output.trim().slice(0, 800) }
      }
    }

    function isMissingCliModule(output: string, exp: string): boolean {
      const normalized = output.replace(/'/g, '"')
      return normalized.includes(`No module named \"src.experiments.${exp}.cli\"`)
    }

    const checks = args.checks ?? ["ruff", "mypy", "import"]
    let allPass = true

    for (const exp of args.experiments) {
      lines.push(`\n=== ${exp} ===`)

      if (checks.includes("ruff")) {
        const r = run(`uv run ruff check src/experiments/${exp}/`)
        lines.push(`ruff: ${r.ok ? "✓ PASS" : "✗ FAIL"}`)
        if (!r.ok) { lines.push(r.output); allPass = false }
      }

      if (checks.includes("mypy")) {
        const r = run(`uv run mypy src/experiments/${exp}/ --ignore-missing-imports`)
        lines.push(`mypy: ${r.ok ? "✓ PASS" : "✗ FAIL"}`)
        if (!r.ok) { lines.push(r.output); allPass = false }
      }

      if (checks.includes("import")) {
        const r = run(`uv run python -c "import src.experiments.${exp}.run; print('import ok')"`)
        lines.push(`import run.py: ${r.ok ? "✓ PASS" : "✗ FAIL"}`)
        if (!r.ok) { lines.push(r.output); allPass = false }

        const r2 = run(`uv run python -c "import src.experiments.${exp}.cli; print('import ok')"`)
        const missingCli = !r2.ok && isMissingCliModule(r2.output, exp)
        lines.push(`import cli.py: ${r2.ok ? "✓ PASS" : missingCli ? "✗ FAIL (missing cli.py module)" : "✗ FAIL"}`)
        if (!r2.ok) {
          lines.push(r2.output)
          allPass = false
        }
      }

      if (checks.includes("pytest")) {
        const r = run(`uv run pytest tests/ -k "${exp}" -x -q`)
        lines.push(`pytest -k ${exp}: ${r.ok ? "✓ PASS" : "✗ FAIL"}`)
        if (!r.ok) { lines.push(r.output); allPass = false }
      }
    }

    lines.unshift(allPass ? "OVERALL: ✓ ALL PASS" : "OVERALL: ✗ FAILURES DETECTED")
    return lines.join("\n")
  },
})
