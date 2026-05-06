# Feature Specification: Dataset Restructure and Derivation

**Feature Branch**: `005-dataset-restructure`  
**Created**: 2026-05-05  
**Status**: Draft  
**Input**: User description: "I want to work with dataset First, help me define dataset structure into instruction rule, restructure/rename the dataset to match content: 1. Dataset/original: each species has 4-7 strains, cyclopium has only 1 strain. Used in @repos/fungal-cv-qdrant/src/experiments/retrieval/run.py for taking one strain our and finetune, extract features from the rest image. Also use to train yolo manual label data. 2. Dataset/new_data: about 1-2 strain per species, the quality of image is worse, less environment. @repos/fungal-cv-qdrant/src/utils/reformat_dataset.py @repos/fungal-cv-qdrant/src/utils/reformat_dataset_yolo.py create derived dataset. Explore the derived structure and analyze. I want to rename the dataset for better readability, fix @repos/fungal-cv-qdrant/src/utils/reformat_dataset.py @repos/fungal-cv-qdrant/src/utils/reformat_dataset_yolo.py to only one script and one dataset will has only 1. Reformat hierarchical dataset with structure {species}/{strain}/{environment}/filename. 2. Reformat both dataset, include visualize with bounding boxes image using kmeans + kmeans pipeline visualization, 3 segments in segments_{method}/ folder with same name. We have segments_yolo, segments_kmeans. 3. Remove the redundant full_image, segmented images in Dataset/ with redundant metdata 4. Fix related code @repos/fungal-cv-qdrant/src/config.py Then, test the fix to make sure it works, related code works. Then, add isntruction about how to use the dataset. Setup the quickest way to sync up dataset to our drive, and quickly download for vast ai machine."

## Table of Contents

- [Affected Contexts](#affected-contexts-mandatory)
- [User Scenarios & Testing](#user-scenarios--testing-mandatory)
- [Requirements](#requirements-mandatory)
- [Success Criteria](#success-criteria-mandatory)
- [Definition of Done](#definition-of-done-mandatory)
- [Assumptions](#assumptions)

## Affected Contexts *(mandatory)*

- **Primary Repo**: `repos/fungal-cv-qdrant`
- **Additional Touched Repos**: None
- **Shared Artifacts**: `Dataset/`, derived dataset images, derived dataset metadata, dataset usage instructions, dataset sync workflow for Drive and Vast.ai
- **Execution Tooling**: `uv`/`uvx` for Python workflows, shell commands for filesystem validation, `gh` only if workflow checks are later needed
- **Experiment Dependency**: Retrieval evaluation in `repos/fungal-cv-qdrant/src/experiments/retrieval/run.py` consumes strain/species/environment-organized derived dataset outputs and strain-species mapping from `Dataset/`
- **Reimplementation Boundary**: N/A; work stays inside `repos/fungal-cv-qdrant` and shared dataset artifacts

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Build readable canonical dataset (Priority: P1)

As a researcher, I want one canonical dataset layout with clear names and predictable folders so that I can understand what data is source material versus derived segmentation output without reading utility code.

**Why this priority**: Dataset readability and stable layout are foundation for every downstream experiment, labeling workflow, and remote sync task.

**Independent Test**: Can be fully tested by running dataset reformatting once on both source collections and verifying resulting folders, filenames, and metadata match documented rules.

**Acceptance Scenarios**:

1. **Given** original and new dataset image sources are available, **When** researcher runs canonical dataset preparation, **Then** system produces one readable hierarchical dataset organized as `{species}/{strain}/{environment}/filename`.
2. **Given** canonical dataset has been prepared, **When** researcher inspects derived outputs, **Then** source images and segmentation outputs are separated by purpose and no redundant top-level copies remain.

---

### User Story 2 - Produce both segmentation views for review (Priority: P2)

As a researcher, I want both KMeans-derived and YOLO-derived segment outputs plus bounding-box visualizations so that I can compare segmentation quality and inspect failures quickly.

**Why this priority**: Segmentation review is required to trust derived retrieval inputs and to debug lower-quality new data.

**Independent Test**: Can be fully tested by preparing derived data for sample images and verifying visualization images, segment folders, and segment counts are created for both methods.

**Acceptance Scenarios**:

1. **Given** canonical dataset preparation runs on an image, **When** segmentation succeeds, **Then** system stores method-specific segment outputs under `segments_kmeans/` and `segments_contour/` using matching names for same parent image.
2. **Given** segmentation outputs are created, **When** researcher opens visualization outputs, **Then** each image shows bounding boxes and pipeline visualization needed to inspect how segments were produced.

---

### User Story 3 - Keep retrieval and sync workflows usable (Priority: P3)

As a researcher using local and Vast.ai environments, I want retrieval code, dataset instructions, and sync steps updated to match renamed dataset paths so that I can prepare data locally, upload it to Drive, and download it remotely without manual path repair.

**Why this priority**: Documentation and sync stability prevent breakage after renaming and are needed for day-to-day usage, but they depend on canonical dataset layout already being defined.

**Independent Test**: Can be fully tested by updating related configuration, running affected preparation code, and executing documented sync plan or dry-run against expected paths.

**Acceptance Scenarios**:

1. **Given** dataset paths have been renamed, **When** retrieval-related code and configuration access dataset artifacts, **Then** they resolve current canonical locations without relying on removed redundant folders.
2. **Given** researcher follows usage instructions on local machine or Vast.ai machine, **When** they run documented sync commands, **Then** they can upload and download dataset artifacts through one short, repeatable workflow.

### Edge Cases

- What happens when a species has only one strain and cannot support same split assumptions as species with many strains?
- How does system handle images whose filenames do not cleanly encode strain, environment, or angle metadata?
- What happens when one segmentation method produces fewer than three usable segments or no detections for an image?
- How does system avoid collisions when different source datasets contain images with same filename?
- What happens when new low-quality data lacks environments present in original data?
- How does sync workflow behave when only subset of dataset artifacts should be uploaded or downloaded?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST define and document human-readable names and intended use for each source dataset collection currently stored under `Dataset/`, including training-grade source data and lower-quality incoming data.
- **FR-002**: System MUST provide one canonical derived dataset layout organized as `{species}/{strain}/{environment}/filename`.
- **FR-003**: System MUST consolidate current dataset reformatting behavior into one maintained preparation entrypoint instead of separate KMeans-only and YOLO-only scripts.
- **FR-004**: System MUST accept both source dataset collections as input to the canonical preparation flow and preserve source provenance for each prepared item.
- **FR-005**: System MUST generate KMeans-based segmentation outputs and YOLO-based segmentation outputs for prepared dataset items when required inputs for each method are available.
- **FR-006**: System MUST store method-specific segment images in `segments_kmeans/` and `segments_contour/` folders using matching parent-image naming so outputs from both methods can be compared directly.
- **FR-007**: System MUST produce per-image visualization artifacts that show bounding boxes and segmentation-review context for each enabled segmentation method.
- **FR-008**: System MUST keep segmentation outputs and metadata sufficient for retrieval evaluation and downstream inspection without preserving redundant top-level `full_image` and `segmented_image` copies.
- **FR-009**: System MUST remove or stop generating redundant dataset metadata files when same information can be derived from canonical structure and retained artifact records.
- **FR-010**: System MUST update dataset-related configuration so all supported code paths resolve renamed canonical dataset locations.
- **FR-011**: System MUST keep retrieval evaluation workflows compatible with canonical dataset outputs used for strain holdout and feature extraction.
- **FR-012**: System MUST preserve or regenerate strain-to-species mapping required by retrieval evaluation and dataset preparation.
- **FR-013**: System MUST fail with clear messages when required source folders, weights, or metadata are missing.
- **FR-014**: Users MUST be able to prepare only selected source collections or selected subsets without rebuilding unrelated dataset artifacts.
- **FR-015**: System MUST provide instructions that explain dataset purpose, canonical folder layout, preparation flow, and segmentation artifact meaning.
- **FR-016**: System MUST provide shortest supported sync workflow for uploading dataset artifacts to shared Drive and downloading them onto Vast.ai machines.
- **FR-017**: System MUST keep sync instructions aligned with canonical dataset names and folder paths after rename.

### Key Entities *(include if feature involves data)*

- **Source Dataset Collection**: Named image collection with defined quality level, intended use, and provenance such as holdout/fine-tuning source data or lower-quality incoming data.
- **Canonical Dataset Item**: Prepared image record identified by species, strain, environment, source collection, filename, and parsed image metadata.
- **Segmentation Artifact Set**: All derived outputs for one image, including method-specific segments and visualization assets for KMeans and YOLO.
- **Strain-Species Mapping**: Lookup that connects strain identifiers to species labels for dataset preparation and retrieval evaluation.
- **Sync Profile**: Documented local-to-Drive and Drive-to-Vast.ai transfer path definition for dataset artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of prepared dataset items can be located by species, strain, and environment using documented canonical folder rules alone.
- **SC-002**: Researchers can prepare both source dataset collections with one documented command flow in under 10 minutes of setup time, excluding model download time and image processing runtime.
- **SC-003**: 100% of reviewed sample images that are processed by both segmentation methods produce directly comparable method-specific outputs with matching parent-image names.
- **SC-004**: Retrieval preparation and evaluation workflows complete against renamed dataset paths without manual path edits.
- **SC-005**: Researchers can complete dataset upload to shared Drive and dataset download to Vast.ai by following one documented workflow without consulting utility source code.

## Definition of Done *(mandatory)*

### Verification Evidence

- **Local Checks**: Relevant `uv --directory repos/fungal-cv-qdrant ...` validation for dataset preparation entrypoint, retrieval-related smoke checks, and any repo-standard Python checks added or updated for touched code
- **Workflow Checks**: Relevant GitHub workflow checks if available for `repos/fungal-cv-qdrant`, otherwise N/A
- **Manual Validation**: Inspect sample canonical dataset tree, inspect sample `segments_kmeans/` and `segments_contour/` outputs plus bounding-box visualizations, confirm documented Drive/Vast.ai sync steps on dry-run or safe subset
- **PR Evidence**: Summary of renamed dataset structure, before/after artifact layout, commands used for validation, sample output paths, and updated usage/sync documentation

## Assumptions

- Existing source collections under `Dataset/original` and `Dataset/new_data` remain authoritative inputs until rename is completed.
- Retrieval workflows continue to depend on strain/species/environment metadata and do not require full-resolution duplicate image copies once canonical outputs exist.
- YOLO-based segmentation may require external weights or service access, so canonical flow may allow method-by-method execution when one segmentation backend is unavailable.
- Shared Drive sync should use existing monorepo-supported dataset sync tooling rather than a new transfer mechanism.
- Dataset rename and restructuring are experiment-context changes only and do not require backend or frontend code changes in this feature.
