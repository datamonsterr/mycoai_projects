# Rule: Graduation Report Content Writing

## Scope

This rule applies to writing/editing graduation thesis source in `graduation_report/`, especially chapter files and related assets that replaced the old `docs/graduation_report/` tree. Derived from mistake review of `02-retrieval-model.md`.

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

## Rule Priority

Rule 2 > Rule 3 > Rule 1. Depth first, visuals second, cleanup code blocks last.
