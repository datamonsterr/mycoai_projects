# Feature Specification: YOLO Dataset Pipeline

**Feature Branch**: `002-yolo-dataset-pipeline`  
**Created**: 2026-04-22  
**Status**: Draft  
**Input**: User description: "Investigate Dataset/manual_labeled_data_roboflow. Write a script to: 1. Read the DTO_XXX-XX for strain and map with the specy name, strain to specy csv 2. Create a new folder with same structure but label by specy not all the same like currently 3. Create yolo train for segmentation, using this label by colony data 4. Create yolo train for species classification cross validation @fungal-cv-qdrant/report/cross_validation/ . Store the results/cross_validation_yolo/ with a csv for K folds information and necessary information to analyze the result, visualization 5. Create report for experimenting yolo for segmentation and cross validation train/test. 6. Note that for cross validation we use train test split by taking one strain in a species not the train / test /valid in Dataset/manual_labeled_data_roboflow. The train/test/split random is for segmentation."

## Table of Contents

- [Affected Contexts](#affected-contexts-mandatory)
- [User Scenarios & Testing](#user-scenarios--testing-mandatory)
- [Requirements](#requirements-mandatory)
- [Success Criteria](#success-criteria-mandatory)
- [Definition of Done](#definition-of-done-mandatory)
- [Assumptions](#assumptions)

## Affected Contexts *(mandatory)*

- **Primary Repo**: fungal-cv-qdrant
- **Additional Touched Repos**: None
- **Shared Artifacts**: `Dataset/manual_labeled_data_roboflow/`, `Dataset/strain_to_specy.csv`, derived labeled dataset folders under `Dataset/`, reports under `fungal-cv-qdrant/report/`, and experiment outputs under `results/cross_validation_yolo/`
- **Execution Tooling**: `uv`/`uvx` for Python workflows
- **Experiment Dependency**: Uses `fungal-cv-qdrant/report/cross_validation/` as the reporting baseline for the species classification evaluation flow and produces new YOLO-based cross-validation artifacts for comparison
- **Reimplementation Boundary**: N/A

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build species-labeled training data (Priority: P1)

A researcher can transform the manually labeled Roboflow dataset into a new dataset structure where each colony annotation is labeled with the mapped species instead of a single generic class.

**Why this priority**: All downstream segmentation and classification experiments depend on correct species-aware labels, so this is the minimum valuable slice.

**Independent Test**: Can be fully tested by running the dataset preparation script on `Dataset/manual_labeled_data_roboflow/` and verifying that the output folder preserves split structure, image-label pairing, and species-specific class assignments derived from `Dataset/strain_to_specy.csv`.

**Acceptance Scenarios**:

1. **Given** an input image filename containing a DTO strain identifier and a matching row in the strain-to-species mapping, **When** the preparation script processes the sample, **Then** the output label uses the mapped species class rather than the existing generic class.
2. **Given** the source dataset contains `train`, `valid`, and `test` split folders, **When** the preparation script completes, **Then** the output dataset preserves the same split layout and file pairings for every successfully mapped sample.

---

### User Story 2 - Train YOLO segmentation on colony labels (Priority: P2)

A researcher can launch a segmentation training run using the species-labeled colony dataset and obtain reproducible training outputs and summary metrics.

**Why this priority**: Once the dataset is corrected, segmentation training is the first model experiment needed to validate whether species-aware labels improve colony segmentation workflows.

**Independent Test**: Can be fully tested by running the segmentation experiment entrypoint on the derived dataset and confirming that it produces a run record, training outputs, and a report-ready summary of the dataset and metrics used.

**Acceptance Scenarios**:

1. **Given** the species-labeled dataset is available, **When** a segmentation training run is started, **Then** the system uses a random split strategy based on the derived segmentation dataset rather than the strain-held-out cross-validation logic.
2. **Given** a segmentation run finishes, **When** the researcher inspects the outputs, **Then** the run includes the dataset identity, training configuration summary, and performance metrics needed for reporting.

---

### User Story 3 - Evaluate species classification with strain-held-out cross validation (Priority: P3)

A researcher can run species classification cross validation where each fold holds out one strain per species for testing, collect fold-by-fold metrics, and review a summarized analysis report with visualizations.

**Why this priority**: This is the key experiment for assessing generalization across strains and is more valuable after the data preparation and segmentation workflow are in place.

**Independent Test**: Can be fully tested by executing the cross-validation workflow and verifying that each fold records the held-out strains, train/test membership, per-fold metrics, aggregate metrics, and generated visualizations under `results/cross_validation_yolo/`.

**Acceptance Scenarios**:

1. **Given** species each contain multiple strains in the mapping file, **When** the cross-validation workflow creates folds, **Then** each fold selects one strain per species for testing and excludes those strains from that fold’s training set.
2. **Given** all folds have completed, **When** the workflow writes results, **Then** it produces a CSV with fold-level details and enough metadata to analyze outcomes across species, strains, and folds.
3. **Given** the reporting step runs after training, **When** the report is generated, **Then** it summarizes segmentation and classification experiments and includes visual evidence that supports train/test interpretation.

### Edge Cases

- A source filename contains a DTO identifier that does not appear in `Dataset/strain_to_specy.csv`.
- Multiple filenames resolve to the same strain but belong to different media or capture conditions that must still remain in the correct output split.
- A species has too few strains to support the requested strain-held-out fold construction.
- A label file is missing, empty, or malformed for an otherwise valid image.
- A fold finishes with no test samples for a species because the source mapping or data inventory is incomplete.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read strain identifiers from `Dataset/manual_labeled_data_roboflow/` sample filenames using the `DTO_XXX-XX` pattern and map each identifier to a species using `Dataset/strain_to_specy.csv`.
- **FR-002**: The system MUST normalize strain identifiers consistently between filenames and the mapping source so that `DTO_XXX-XX` filenames can be matched to `DTO XXX-XX` mapping rows.
- **FR-003**: The system MUST create a new derived dataset folder that preserves the source directory structure and image-label pairing while replacing the current generic colony label with the mapped species label for each colony annotation.
- **FR-004**: The system MUST produce a species class manifest for the derived dataset so class names and class indices remain stable across dataset generation, training, and reporting.
- **FR-005**: The system MUST record any skipped or failed samples, including missing strain mappings, missing labels, and unreadable files, in a machine-readable summary that researchers can review.
- **FR-006**: The system MUST support a segmentation training workflow that uses the species-labeled colony dataset and treats the segmentation split as a random train/validation/test partition rather than a strain-held-out evaluation.
- **FR-007**: The system MUST capture segmentation experiment outputs and summary metrics in a form that can be referenced from the experiment report.
- **FR-008**: The system MUST support a species classification cross-validation workflow that ignores the existing `train`, `valid`, and `test` split folders in `Dataset/manual_labeled_data_roboflow/` when assigning cross-validation train/test membership.
- **FR-009**: The system MUST construct each classification fold by selecting one strain per species for testing and assigning all remaining eligible strains for those species to training in that fold.
- **FR-010**: The system MUST fail fast with a clear explanation when a species does not have enough distinct strains to satisfy the requested fold strategy.
- **FR-011**: The system MUST store classification cross-validation outputs under `results/cross_validation_yolo/`.
- **FR-012**: The system MUST write a CSV in `results/cross_validation_yolo/` containing, for every fold, the fold identifier, held-out strain per species, sample counts, metric values, and the metadata needed to analyze outcomes by fold, species, and strain.
- **FR-013**: The system MUST generate visual summaries for the cross-validation results that allow researchers to compare fold performance and inspect train/test behavior.
- **FR-014**: The system MUST create a report for the YOLO segmentation experiment and the YOLO cross-validation classification experiment that documents dataset provenance, split strategy, key metrics, and generated visualizations.
- **FR-015**: Users MUST be able to run dataset preparation, segmentation training, cross-validation training, and report generation as separate steps so intermediate artifacts can be inspected independently.

### Key Entities *(include if feature involves data)*

- **Strain Mapping Record**: A mapping entry that links a strain identifier to a species name and indicates any existing test designation present in the source CSV.
- **Derived Species-Labeled Dataset**: A copy of the manual labeled dataset with preserved split structure and species-specific class labels for colony annotations.
- **Segmentation Experiment Run**: A record of one training attempt on the species-labeled dataset, including dataset identity, metrics, and output locations.
- **Cross-Validation Fold Record**: A per-fold summary capturing the held-out strains, training/test sample counts, metric values, and any fold-level warnings.
- **YOLO Experiment Report**: A report artifact summarizing the segmentation and cross-validation experiments, their data sources, and their visual analysis outputs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Researchers can generate the species-labeled derivative of `Dataset/manual_labeled_data_roboflow/` in one run, with 100% of successfully mapped samples retaining their original split placement and image-label pairing.
- **SC-002**: The dataset preparation summary reports every unmapped, missing, or malformed sample so that no processed sample has an unexplained label state.
- **SC-003**: For every completed classification fold, the recorded outputs identify exactly one held-out strain per species in the test set and zero overlap between a fold’s held-out strains and its training strains.
- **SC-004**: The cross-validation results folder contains one aggregate CSV and corresponding visual summaries that let a researcher compare fold performance without manually reconstructing the split assignments.
- **SC-005**: The experiment report enables a reviewer to understand the data source, split strategy, and outcome of both the segmentation and classification workflows in under 10 minutes.

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: Relevant `uv --directory fungal-cv-qdrant ...` commands for dataset preparation, segmentation training, cross-validation execution, and report generation; any repo-standard lint, format, type, and test commands discovered for touched Python code
- **Workflow Checks**: Relevant GitHub workflow or `gh` verification if a workflow exists for these experiment/report paths, otherwise N/A
- **Manual Validation**: Review the generated dataset tree, inspect at least one relabeled annotation per species, and verify the cross-validation CSV and visual summaries match the documented fold strategy
- **PR Evidence**: Command transcript, output paths, summary tables, generated figures, and a note explaining the difference between random segmentation splits and strain-held-out classification folds

## Assumptions

- The target users are researchers working inside `fungal-cv-qdrant` who can run experiment scripts locally with access to the shared `Dataset/` and `results/` directories.
- `Dataset/strain_to_specy.csv` is the authoritative source for mapping strain identifiers to species names for this workflow.
- The current Roboflow dataset uses a single generic colony label, and relabeling only changes class identity rather than annotation geometry.
- Random train/validation/test splitting is only required for segmentation experiments derived from the relabeled dataset.
- Strain-held-out cross validation for species classification is defined by species-level strain selection and does not reuse the existing Roboflow split membership.
- The new report may extend the existing `fungal-cv-qdrant/report/cross_validation/` reporting context but remains focused on the YOLO experiments requested here.
