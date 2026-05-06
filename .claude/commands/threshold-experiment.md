Run one new Autolab experiment pass for the threshold experiment on top of the refreshed segmented diverse retrieval baseline.

Assume `/threshold-setup` has already been completed successfully.
If the retrieval CSV is stale, incomplete, or still based on the old retrieval path, run `/threshold-setup` first.

## Mission

Improve threshold F1 via the Autolab multi-agent loop. The refreshed segmented diverse retrieval CSV is the canonical source for `s0_score..s4_score`.

## Do not change

- the known-vs-unknown label meaning
- the primary experiment score definition
- the staircase interpretation rules in `.opencode/rules/experiment-visualization.md`

## Allowed directions

- retrieval implementation fixes
- known-test-strain inclusion fixes
- segmented query grouping fixes
- environment handling fixes
- neighbor filtering fixes
- formula generation and threshold methodology improvements
- logging improvements
- threshold-aware visualization improvements
- any other implementation change that can improve F1 without changing the score definition

## Workflow for each Autolab pass

1. Launch opencode and invoke the Autolab agent:

```bash
opencode
```

2. Prompt:

```
run one autoresearch pass on threshold experiment. Use the refreshed segmented retrieval at results/threshold/diverse_retrieval_results.csv.
```

Autolab delegates to `@researcher` (optional literature scan), `@planner` (queue hypotheses), `@worker` (isolated worktree run), and `@reporter` (status summary).

3. Interpret results. After the pass:

- `results/autoresearch/threshold.csv` + `.png` updated via the staircase visualization rules
- `repos/fungal-cv-qdrant/research/results.tsv` has new rows
- `@reporter` output shows best F1, strategy name, staircase path

## Before each new pass

Review current state:

- `results/threshold/diverse_retrieval_results.csv`
- `results/threshold/log/experiments.log`
- `results/threshold/log/best_strategy.json`
- `results/threshold/log/all_experiments.csv`
- `results/autoresearch/threshold.csv`
- `results/autoresearch/threshold.png`
- `repos/fungal-cv-qdrant/research/results.tsv`

Confirm the retrieval CSV is still the refreshed segmented test-set version before trusting any threshold result.

## After each new best

Generate threshold-aware prediction visualizations:

```bash
uv run python -m src.analysis.visualization.visualize_prediction
```

The final decision shown must be the thresholded `known` or `unknown` output from the winning formula.

Each new-best visualization must show:
- formula name, algorithm name, threshold value
- formula score, binary prediction, ground-truth label
- ranked neighbor species as supporting context
- segmented diverse query images and DB segmented neighbors

## After each pass

- Check `@reporter` for status
- If new running best found, merge the winning worker branch to `autoresearch/threshold`:
  ```bash
  git -C repos/fungal-cv-qdrant checkout autoresearch/threshold
  git -C repos/fungal-cv-qdrant merge autoresearch/threshold/{N}-{summary}
  ```
- If not a new best, the branch remains as historical record.

## Loop rule

Repeat the Autolab cycle:

1. launch opencode → prompt Autolab for one threshold pass
2. check `@reporter` for status
3. inspect prior bests and prior failures
4. fix the implementation based on the latest logged findings
5. re-run Autolab
6. if new best, generate threshold-aware visualizations and dig deeper

## Suggested search strategy

Use the latest running best formula family as the center of gravity. Each pass should:
- inspect the current best formula family
- identify the likely implementation or methodological weakness
- make one focused improvement
- re-run through Autolab
- keep only improvements that move the running best upward

## Key files

- `src/experiments/threshold/prepare_test_strains.py`
- `src/experiments/threshold/retrieve_diverse.py`
- `src/experiments/threshold/threshold_analysis.py`
- `src/experiments/threshold/expanded_threshold_analysis.py`
- `src/experiments/threshold/run.py`
- `src/analysis/visualization/visualize_prediction.py`
- `.opencode/rules/experiment-visualization.md`
- `.opencode/agents/autolab.md`
- `.opencode/agents/worker.md`
- `.opencode/agents/reporter.md`
