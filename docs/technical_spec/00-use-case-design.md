# Technical Spec: Use Case Design

## Overview

The system supports authenticated fungal species retrieval, feedback/contribution review, Data Owner data indexing, metadata management, dataset governance, user administration, Qdrant re-indexing, and Candidate Model assessment.

Source of truth: `../SRS.md`.

![Use case diagram](../assets/use-case-diagram.png)

## Actors

| Actor | Scope |
|-------|-------|
| User | Authenticated species retrieval and feedback/contribution submission from retrieval results |
| Data Owner | All User use cases plus reference-data indexing, metadata, dataset, user, model, and index governance |

## Use Cases

### Authenticate User

All actors authenticate before protected workflows. Users may self-register or accept invitations. The initial Data Owner is provisioned internally by script using user email; later role changes may be managed by Data Owner role promotion.

### Retrieve Species

Users and Data Owners retrieve species from strain images. Retrieve Species includes:

1. Authenticate User
2. Prepare Segmented Images
3. View ranked results
4. Download batch results when using batch retrieval

Prepare Segmented Images includes:

1. Upload single image or batch folder
2. Download Batch Template Folder when needed
3. Provide strain and media metadata
4. Auto segment with AI
5. Edit bounding boxes
6. Remove unwanted images/segments before processing

Known Media uses same-media KNN by default. New/other Media uses all-media KNN and is flagged for Data Owner review.

### Submit Feedback

Submit Feedback extends Retrieve Species. Users may submit wrong-prediction feedback or contribution proposals only from retrieval results. Users cannot browse the reference dataset.

Accepted contribution feedback becomes pending reference data; Data Owner reviews metadata and bounding boxes before indexing.

### Index New Data

Data Owners index new reference data for known species. Index New Data includes:

1. Authenticate User
2. Prepare Segmented Images
3. Manage Metadata

Index New Data does **not** include Retrieve Species. It reuses upload, segmentation, and bounding-box review, but bypasses prediction because species metadata is supplied by Data Owner or accepted through review.

### Manage Metadata

Data Owners CRUD Species and Media. Strain is dataset metadata/entity, not a managed metadata catalog.

### Manage Users

Data Owners invite Users, manage account status, and promote/demote roles while preserving at least one active Data Owner.

### Manage Dataset

Data Owners browse/search/filter/group by strain, media, and species; edit image metadata; archive/restore items; and view Data Update Status. Permanent delete is not supported.

### Maintain Model and Index

Data Owners can trigger Qdrant re-indexing in-system. Deep feature-extractor retraining is external; the system warns when accumulated reference-data changes require retraining and provides Python guidance for dataset download, retraining, and model reupload. Data Owners upload Candidate Models, assess them against a fixed evaluation set, compare with current results, and manually promote or reject.

## Diagram Relationships

| Relationship | Type |
|---|---|
| Retrieve Species -> Authenticate User | `<<include>>` |
| Retrieve Species -> Prepare Segmented Images | `<<include>>` |
| Index New Data -> Authenticate User | `<<include>>` |
| Index New Data -> Prepare Segmented Images | `<<include>>` |
| Index New Data -> Manage Metadata | `<<include>>` |
| Submit Feedback -> Retrieve Species | `<<extend>>` |
| Manage Metadata -> Authenticate User | `<<include>>` |
| Manage Users -> Authenticate User | `<<include>>` |
| Manage Dataset -> Authenticate User | `<<include>>` |
| Maintain Model and Index -> Authenticate User | `<<include>>` |

## Rejected Design Notes

| Rejected Idea | Reason |
|---|---|
| Use "Normal User" | SRS has exactly two actors; canonical term is User. |
| Make Index New Data include Retrieve Species | Indexing bypasses prediction and only shares preparation flow. |
| Allow Users to browse dataset | Users submit feedback from retrieval results only. |
| Permanent delete | Archive preserves auditability and retraining/index trace. |
| In-system deep retraining trigger | Deep retraining is external; only Qdrant re-indexing is in-system. |
