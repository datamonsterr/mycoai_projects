# Rule: Graduation Report Content Writing

## Scope

This rule applies to writing/editing graduation thesis source in `graduation_report/`, especially chapter files and related assets. `docs/graduation_report/` is now the control plane for report work and must be read before thesis edits. Derived from mistake review of `02-retrieval-model.md`.

## Mandatory pre-read

Before editing thesis content, read in this order:
1. `docs/graduation_report/README.md`
2. `docs/graduation_report/reviews/`
3. `docs/graduation_report/plans/`
4. `docs/graduation_report/rules/`

Do not update `graduation_report/` first and rationalize later. Review, plan, rules, and evidence context come first.

## Figure source-of-truth

- `graduation_report/figures/` stores generated artifacts only.
- `docs/graduation_report/code/` stores generator source for charts, tables, and diagrams.
- Prefer fixing generator code and regenerating assets over manual figure edits.

## Agent mode rule

Report workflow agents must be configured as `mode: subagent`, not primary agents. Use delegation through an orchestrator or an existing primary agent rather than promoting report-specialist agents to primary mode.

## Context7 / opencode config rule

When changing `.opencode/` configuration for report workflow, validate field shapes against current OpenCode config schema. In particular:
- `mcp.context7` should remain a remote MCP server entry with `type`, `url`, and optional `enabled` / `timeout` fields.
- report-specialist agents belong under `.opencode/agents/` and remain `mode: subagent`.
- project instructions should include this report rule so docs-first workflow is always loaded.

If config shape is uncertain, check `https://opencode.ai/config.json` before editing.

## Rule 1: Prefer Math Expressions and Plain English Over Code


## Rule 1: Prefer Math Expressions and Plain English Over Code

- **Mistake**: Using Python `lstlisting` blocks to explain algorithms (K-Means Local K=2, KNN aggregation).
- **Correct rule**: Express algorithms as mathematical notation or plain English step-by-step descriptions. Code listings belong in appendices or implementation docs, not in the main body.
- **Example fix**: Instead of:
  ```
  \begin{lstlisting}[language=Python, caption=KNN Prediction Aggregation]
  for specy, total_score in species_scores.items():
      if strategy == "weighted":
          final_score = total_score / total_neighbors
  \end{lstlisting}
  ```
  Write:
  > The **weighted aggregation** computes the final score for each candidate species \(c\) as:
  > \[
  > S_c = \frac{\sum_{i} s_{i,c}}{\sum_{i} n_{i,c}}
  > \]
  > where \(s_{i,c}\) is the similarity score of the neighbor(s) belonging to species \(c\) from query segment \(i\), and \(n_{i,c}\) is the number of times species \(c\) appears among retrieved neighbors.

## Rule 2: Dive Deep — Include All Available Research Data

- **Mistake**: Surface-level descriptions that omit experiments already completed (cross_validation, yolo_segmentation, fine-tuning results, triplet loss findings, kmeans flare issues).
- **Correct rule**: Before writing, inventory ALL completed experiments and reports in:
  - `research/report/final_gr2/` (FINAL_REPORT.md, COMPREHENSIVE_REPORT.md)
  - `research/report/cross_validation/`
  - `research/report/kmeans_segmentation/`
  - `research/src/experiments/cross_validation/`
  - `research/src/experiments/yolo_segmentation/`
  - `research/src/experiments/kmeans_segmentation/`
  
  Every experiment family should appear in the chapter. Cross-reference findings.
- **Example fix**: The old chapter omitted the cross-validation experiment (5-fold strain-level with 100 total runs), YOLO segmentation alternative, fine-tuning training curves, triplet loss failure analysis, t-SNE environment invariance finding, and kmeans flare problem. Include all.

## Rule 3: For Each Experiment, Add Visual Evidence

- **Mistake**: Describing experiments in prose only, no images, charts, or data tables.
- **Correct rule**: For every experiment/methodology section, include at minimum:
  - **Data table**: Key metrics (accuracy, F1, parameters)
  - **Chart**: Training curves, accuracy vs K, fold variance box plots, confusion matrices, staircase charts
  - **Image**: Example segmentation results, prediction visualizations
  - **Algorithm flow diagram**: For the methodology section (pipeline diagram showing data flow between components)
- **Example fix**: The retrieval experiments section should include the staircase chart, per-species accuracy table, confusion matrix, and prediction visualization examples.

## Rule 4: Define Symbols, Acronyms, and Short Codes at Point of Use

- **Mistake**: Using internal shorthand such as `E1`, `E2`, `E3`, `s0`, `s1`, or unnamed collection labels without explanation.
- **Correct rule**: Every acronym, symbol, short code, and experiment shorthand must be defined where the reader first sees it.
- **Allowed locations for definition**:
  - first paragraph that introduces the term
  - figure caption
  - table caption
  - chart legend
  - axis note
- **Chart/diagram exception**: Short labels may appear inside figures, charts, and diagrams, but the caption, legend, or first referencing paragraph must define them clearly.
- **Reader rule**: A reader with no codebase access must still understand the term.

## Rule 5: Every Figure Must Support a Finding

- **Mistake**: Figures inserted as decoration, or text that only says "Figure X.X shows ..." without analysis.
- **Correct rule**: Every figure needs three parts:
  1. short lead-in sentence before figure
  2. explicit reference in body text
  3. finding after figure that states why it matters
- **Example fix**: Do not write only "Figure 2.7 shows aggregation results." Write what comparison the figure supports, what trend appears, and what decision follows from it.

## Rule Priority

Rule 2 > Rule 3 > Rule 5 > Rule 4 > Rule 1. Depth first, visuals second, findings third, term clarity fourth, cleanup code blocks last.
