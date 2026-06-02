# Software Requirements Specification: MycoAI Retrieval

## 1. Purpose

This SRS defines functional and non-functional requirements for MycoAI Retrieval, a system for authenticated fungal image upload, segmentation, species retrieval, reference-data indexing, dataset governance, user management, and model/index maintenance.

## 2. Scope

The system supports two actors: **User** and **Data Owner**. A User retrieves species predictions from uploaded fungal strain images and submits feedback or contribution proposals. A Data Owner has all User capabilities plus authority to manage metadata, users, dataset records, Qdrant indexing, and candidate model assessment.

## 3. Domain Language

Use `CONTEXT.md` as terminology source of truth.

| Term | Meaning |
|---|---|
| User | Authenticated person who retrieves fungal species predictions from uploaded strain images. |
| Data Owner | Privileged user responsible for dataset governance, metadata, users, model assessment, and indexing reference data. |
| Image Metadata | Species, strain, media, and related descriptive fields attached to an uploaded fungal image. |
| Species | Managed metadata value identifying fungal taxon associated with reference data or predicted by retrieval. |
| Media | Managed metadata value identifying growth medium used for a fungal image. |
| Strain | Image metadata identifying fungal isolate represented by one or more uploaded images. |
| Feedback | User correction, issue report, or contribution proposal from retrieval results reviewed by Data Owner. |
| Archive | Reversible removal state excluding data from retrieval/indexing without permanent delete. |
| Candidate Model | Uploaded model version awaiting fixed-set assessment before promotion. |
| Data Update Status | Dataset item state: current, changed and requiring re-indexing, or archived. |

## 4. Actors

| Actor | Description | Access Summary |
|---|---|---|
| User | Authenticated retrieval user. | Retrieve species, adjust session bounding boxes, download batch results, submit feedback/contribution proposals. |
| Data Owner | Privileged governance user. | All User access plus index reference data, manage metadata/users/dataset, re-index Qdrant, assess/promote Candidate Models. |

## 5. Use Case Diagram

Diagram type: UML Use Case Diagram.

Diagram content:

```mermaid
usecaseDiagram
actor User
actor "Data Owner" as DataOwner

User --> (Authenticate User)
User --> (Retrieve Species)
User --> (Submit Feedback)

DataOwner --> (Authenticate User)
DataOwner --> (Retrieve Species)
DataOwner --> (Submit Feedback)
DataOwner --> (Index New Data)
DataOwner --> (Manage Metadata)
DataOwner --> (Manage Users)
DataOwner --> (Manage Dataset)
DataOwner --> (Maintain Model and Index)

(Retrieve Species) ..> (Authenticate User) : <<include>>
(Retrieve Species) ..> (Prepare Segmented Images) : <<include>>
(Index New Data) ..> (Authenticate User) : <<include>>
(Index New Data) ..> (Prepare Segmented Images) : <<include>>
(Index New Data) ..> (Manage Metadata) : <<include>>
(Submit Feedback) ..> (Retrieve Species) : <<extend>>
(Manage Metadata) ..> (Authenticate User) : <<include>>
(Manage Users) ..> (Authenticate User) : <<include>>
(Manage Dataset) ..> (Authenticate User) : <<include>>
(Maintain Model and Index) ..> (Authenticate User) : <<include>>
```

Important notes:
- **Prepare Segmented Images** is shared internal behavior, not actor-facing top-level intent.
- **Index New Data** does not include **Retrieve Species**. It reuses upload, segmentation, and bounding-box review, but bypasses species prediction because species metadata is known or supplied by Data Owner.
- **Submit Feedback** extends **Retrieve Species** because feedback is available after retrieval results.
- Data Owner inherits User capabilities.

## 6. Functional Requirements Summary

| ID | Requirement | Actor | Priority | Stability | Verification |
|---|---|---|---|---|---|
| FR-001 | System shall authenticate Users and Data Owners before protected workflows. | User, Data Owner | Must | Stable | Login/session tests |
| FR-002 | System shall allow self-registration and login for Users. | User | Must | Stable | Auth flow tests |
| FR-003 | System shall allow Data Owner to invite Users by onboarding email. | Data Owner | Should | Stable | Invite email tests |
| FR-004 | System shall allow first Data Owner provisioning by internal script using user email. | Data Owner | Must | Stable | Script verification |
| FR-005 | System shall allow Data Owner role promotion after bootstrap. | Data Owner | Must | Stable | RBAC tests |
| FR-006 | System shall retrieve species from single uploaded strain images. | User, Data Owner | Must | Stable | Retrieval tests |
| FR-007 | System shall retrieve species from batch uploaded folders. | User, Data Owner | Must | Evolving | Batch tests |
| FR-008 | System shall provide Batch Template Folder including restructuring instructions. | User, Data Owner | Must | Evolving | Template download test |
| FR-009 | System shall auto-segment images and allow bounding-box edits before retrieval/indexing. | User, Data Owner | Must | Stable | UI/API tests |
| FR-010 | System shall use same-media KNN when uploaded media matches managed Media. | User, Data Owner | Must | Stable | Retrieval strategy tests |
| FR-011 | System shall use all-media KNN when uploaded media is new/other. | User, Data Owner | Must | Stable | Retrieval strategy tests |
| FR-012 | System shall flag new/other Media for Data Owner review. | User, Data Owner | Must | Stable | Review queue tests |
| FR-013 | System shall let Users submit feedback after single or batch retrieval results. | User | Must | Stable | Feedback tests |
| FR-014 | System shall let Users propose retrieved data as database contribution through feedback. | User | Must | Stable | Feedback tests |
| FR-015 | System shall let Data Owner accept/reject feedback and contribution proposals. | Data Owner | Must | Stable | Review workflow tests |
| FR-016 | Accepted contribution feedback shall become pending reference data for Data Owner metadata and bounding-box review before indexing. | Data Owner | Must | Stable | Workflow tests |
| FR-017 | System shall allow Data Owner to index new reference data with species metadata. | Data Owner | Must | Stable | Indexing tests |
| FR-018 | System shall allow Data Owner batch indexing with species metadata in folder structure. | Data Owner | Must | Evolving | Batch indexing tests |
| FR-019 | System shall allow Data Owner to CRUD Species and Media metadata. | Data Owner | Must | Stable | Metadata tests |
| FR-020 | System shall treat Strain as image metadata/dataset entity, not managed label catalog. | Data Owner | Must | Stable | Data model review |
| FR-021 | System shall allow Data Owner to browse/search/filter/group dataset by strain, media, and species. | Data Owner | Must | Stable | Dataset browser tests |
| FR-022 | System shall allow Data Owner to edit image metadata and mark affected item `updated_requires_reindex`. | Data Owner | Must | Stable | Update-status tests |
| FR-023 | System shall allow Archive/Restore only, not permanent delete. | Data Owner | Must | Stable | Archive tests |
| FR-024 | Archived data shall be excluded from retrieval and indexing. | Data Owner | Must | Stable | Retrieval/index tests |
| FR-025 | System shall allow Data Owner to re-index Qdrant in-system after reference-data changes. | Data Owner | Must | Stable | Re-index tests |
| FR-026 | System shall warn Data Owner when accumulated data changes require external deep feature-extractor retraining. | Data Owner | Must | Stable | Warning tests |
| FR-027 | System shall provide Python guidance for dataset download, external retraining, and model reupload. | Data Owner | Must | Evolving | Guidance review |
| FR-028 | System shall allow Data Owner to upload Candidate Model, assess it on fixed evaluation set, compare with current model, and promote/reject manually. | Data Owner | Must | Evolving | Model assessment tests |
| FR-029 | System shall audit all Data Owner mutations. | Data Owner | Must | Stable | Audit tests |

## 7. Use Case Specifications

### UC-001 Authenticate User

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Access protected workflows through authenticated session. |
| Preconditions | Account exists, or User self-registers. Initial Data Owner may be provisioned by internal script. |
| Postconditions | Authenticated session established or access denied. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Actor opens authentication screen.
2. Actor registers or logs in with email and password.
3. System validates credentials.
4. System establishes session and loads actor role.
5. System routes actor to permitted dashboard.

Alternative flows:
- A1 Invalid credentials: system rejects login and shows error.
- A2 Inactive account: system blocks access and shows account status.
- A3 Data Owner invitation: Data Owner sends onboarding email; recipient completes registration.
- A4 First Data Owner setup: internal script assigns Data Owner role to a user email.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | email | Yes | Actor email address. | Must be valid email format. |
| Request | password | Yes | Actor secret. | Must satisfy password policy. |
| Request | name | Registration only | Display name. | Non-empty. |
| Response | session | Yes | Authenticated session/token state. | Returned only after valid credentials. |
| Response | role | Yes | `user` or `owner`. | Controls UI/API permissions. |
| Error | unauthorized | Conditional | Invalid credentials/session. | Return 401. |
| Error | forbidden | Conditional | Authenticated but unauthorized. | Return 403. |

### UC-002 Retrieve Species

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Predict fungal species from uploaded strain images. |
| Includes | Authenticate User, Prepare Segmented Images |
| Preconditions | Actor is authenticated. |
| Postconditions | Ranked species predictions are available; batch CSV may be downloaded; actor may submit feedback. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Actor uploads one image or a batch folder.
2. For batch, actor may download Batch Template Folder and use included instructions to restructure local data before upload.
3. Actor provides image metadata: strain and media. Species is not required for retrieval.
4. System previews uploaded images and metadata.
5. System prepares segmented images through auto-segmentation and bounding-box review.
6. Actor edits/removes bounding boxes if needed.
7. System selects KNN strategy: same-media for managed Media, all-media for new/other Media.
8. System retrieves nearest reference vectors and aggregates predictions across images/segments.
9. System displays ranked species predictions and confidence scores.
10. For batch, system displays batch results and allows CSV download.

Alternative flows:
- A1 New/other Media: system uses all-media KNN, flags Media for Data Owner review, and marks prediction context as new/other Media.
- A2 Invalid upload structure: system rejects batch and shows template mismatch.
- A3 Poor segmentation: actor manually adjusts boxes before processing.
- A4 Removed image: system skips removed batch image.
- A5 No valid segment remains: system blocks retrieval until at least one segment exists.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | images | Yes | Single image or batch folder images. | JPEG/PNG/TIFF, minimum size, max upload size. |
| Request | strain | Yes | Isolate identifier. | Free text, non-empty. |
| Request | media | Yes | Managed Media or new/other Media. | Managed value or flagged free text. |
| Request | max_colonies | No | Max segments per image. | Integer 1-10. |
| Request | bbox_edits | No | Manual box changes. | Must stay within image bounds. |
| Response | predictions | Yes | Ranked species list with scores. | Top results sorted by score. |
| Response | strategy | Yes | Same-media or all-media KNN. | Derived from media status. |
| Response | batch_csv | Batch only | Downloadable result table. | Includes image, strain, media, predicted species, confidence, bbox status, feedback/contribution status. |
| Error | invalid_upload | Conditional | File/folder validation failed. | Show actionable validation message. |

### UC-003 Submit Feedback

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Submit correction, issue report, or contribution proposal from retrieval results. |
| Extends | Retrieve Species |
| Preconditions | Retrieval result exists. |
| Postconditions | Feedback is pending Data Owner review. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Actor views retrieval result.
2. Actor selects submit feedback or contribute result.
3. System pre-fills prediction, strain, media, images, segments, and confidence data.
4. Actor provides corrected species, free-text suggested species, or contribution intent.
5. Actor submits description and optional supporting evidence.
6. System records feedback as pending and notifies Data Owner.

Alternative flows:
- A1 Wrong prediction: actor selects known Species or enters free-text species suggestion.
- A2 Contribution proposal: actor confirms retrieved data may be reviewed for database inclusion.
- A3 Batch feedback: actor submits feedback for one or more batch rows.
- A4 Missing required description: system blocks submission.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | retrieval_result_id | Yes | Source retrieval result. | Must belong to actor or permitted scope. |
| Request | feedback_type | Yes | `wrong_prediction`, `issue`, `contribution`. | Must be valid type. |
| Request | suggested_species | Conditional | Known Species or free text. | Required for wrong prediction when available. |
| Request | description | Yes | Explanation for Data Owner. | Non-empty. |
| Request | supporting_image | No | Additional evidence. | Valid image type/size. |
| Response | feedback_id | Yes | Created feedback identifier. | Status `pending`. |
| Response | status | Yes | Review state. | `pending`, `accepted`, `rejected`, `deferred`. |

### UC-004 Index New Data

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Add known reference data to retrieval database. |
| Includes | Authenticate User, Prepare Segmented Images, Manage Metadata |
| Preconditions | Data Owner authenticated; Species and Media metadata exist or are created during workflow. |
| Postconditions | Reference images/segments are indexed or staged for Qdrant re-indexing. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Data Owner chooses single or batch indexing.
2. Data Owner uploads images or structured batch folder.
3. Data Owner supplies required metadata: species, strain, media.
4. System prepares segmented images.
5. Data Owner reviews images, metadata, and bounding boxes.
6. Data Owner removes unwanted data before submit.
7. System stores accepted images/segments as reference data.
8. System indexes data into Qdrant or marks it for re-indexing.
9. System records audit log.

Alternative flows:
- A1 Missing Species/Media: Data Owner creates metadata through Manage Metadata.
- A2 Batch indexing: system reads species metadata from folder structure/template.
- A3 Accepted contribution feedback: system presents pending reference data for Data Owner review before indexing.
- A4 Bad bounding box: Data Owner fixes boxes using manual labeling tools.
- A5 Existing duplicate: system warns and requires Data Owner decision.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | images/folder | Yes | Reference images or batch folder. | Valid upload/template structure. |
| Request | species | Yes | Managed Species. | Must exist or be created. |
| Request | strain | Yes | Strain metadata. | Non-empty. |
| Request | media | Yes | Managed Media. | Must exist or be created. |
| Request | bbox_edits | No | Reviewed segment boxes. | Must stay within image bounds. |
| Response | dataset_item_id | Yes | Created/updated dataset item. | Audit logged. |
| Response | index_status | Yes | Qdrant indexing state. | `current` or `updated_requires_reindex`. |
| Error | missing_metadata | Conditional | Required metadata absent. | Prompt create/select metadata. |

### UC-005 Manage Metadata

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Maintain Species and Media catalogs used by retrieval/indexing. |
| Includes | Authenticate User |
| Preconditions | Data Owner authenticated. |
| Postconditions | Metadata catalog is updated and audited. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Data Owner opens metadata management.
2. Data Owner creates, updates, archives, or restores Species or Media.
3. System validates uniqueness and references.
4. System warns if metadata change requires re-indexing.
5. System saves change and records audit log.

Alternative flows:
- A1 User submitted new/other Media: Data Owner accepts as new Media or maps to existing Media.
- A2 User suggested free-text species: Data Owner maps to existing Species or creates new Species during feedback review.
- A3 Duplicate metadata: system blocks duplicate value.
- A4 Metadata in use: system warns affected dataset items and Qdrant impact.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | metadata_type | Yes | `species` or `media`. | Strain is not metadata catalog. |
| Request | name | Yes | Metadata display value. | Unique, case-insensitive. |
| Request | description | No | Optional notes. | Stored for Data Owner context. |
| Response | metadata_id | Yes | Created/updated value identifier. | Returned after save. |
| Response | reindex_warning | Conditional | Impact summary. | Shown when references affected. |

### UC-006 Manage Users

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Govern system users and roles. |
| Includes | Authenticate User |
| Preconditions | Data Owner authenticated. |
| Postconditions | User account or role state is updated and audited. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Data Owner opens user management.
2. Data Owner invites user by onboarding email or reviews existing users.
3. Data Owner activates/deactivates users or promotes/demotes roles.
4. System enforces at least one active Data Owner.
5. System records audit log.

Alternative flows:
- A1 Self-registration: User creates account without invite.
- A2 Initial Data Owner: internal script provisions first Data Owner by email.
- A3 Demote last Data Owner: system blocks change.
- A4 Invite already registered email: system shows existing account status.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | email | Yes | Target user email. | Valid email. |
| Request | role | Conditional | `user` or `owner`. | Only Data Owner can change roles. |
| Request | account_status | Conditional | Active/inactive. | Cannot deactivate last Data Owner. |
| Response | user_id | Yes | User identifier. | Updated user returned. |
| Response | onboarding_status | Invite only | Invite state. | Sent, accepted, expired. |

### UC-007 Manage Dataset

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Browse, update, archive, restore, and govern dataset records. |
| Includes | Authenticate User |
| Preconditions | Data Owner authenticated. |
| Postconditions | Dataset state updated; affected items marked for re-index when needed. |
| Priority | Must |
| Stability | Stable |

Main flow:
1. Data Owner opens dataset browser.
2. System shows dataset with search, filter, browse, and group by strain/media/species.
3. Data Owner views images, metadata, segments, and Data Update Status.
4. Data Owner edits metadata or bounding boxes, archives, or restores items.
5. System marks changed items as `updated_requires_reindex` when needed.
6. System excludes archived items from retrieval/indexing.
7. System records audit log.

Alternative flows:
- A1 Archive item: system marks item archived; no permanent delete exists.
- A2 Restore item: system returns item to active state and marks for re-index if needed.
- A3 Metadata edit after indexing: system warns re-index required.
- A4 Bulk update/archive: system shows affected item count and requires confirmation.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | filters | No | Strain/media/species/date/status filters. | Returns matching dataset rows. |
| Request | group_by | No | `strain`, `media`, `species`. | Groups browser results. |
| Request | metadata_update | Conditional | Species/strain/media edits. | Marks `updated_requires_reindex`. |
| Request | archive_action | Conditional | Archive or restore. | No permanent delete. |
| Response | dataset_items | Yes | Matching data rows. | Data Owner only. |
| Response | data_update_status | Yes | `current`, `updated_requires_reindex`, `archived`. | Drives re-index warnings. |

### UC-008 Maintain Model and Index

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Keep Qdrant index and feature-extractor model versions governed. |
| Includes | Authenticate User |
| Preconditions | Data Owner authenticated. |
| Postconditions | Qdrant may be re-indexed; Data Owner may receive retraining guidance; Candidate Model may be promoted/rejected. |
| Priority | Must |
| Stability | Evolving |

Main flow:
1. Data Owner opens model/index dashboard.
2. System shows current model version, index status, changed data count, archived data count, accepted feedback count, and evaluation metrics.
3. Data Owner triggers Qdrant re-index for changed reference data when needed.
4. System runs re-index and updates index status.
5. If many changes accumulate, system warns Data Owner that external deep feature-extractor retraining is recommended.
6. System provides Python guidance to download dataset, retrain externally, and reupload model.
7. Data Owner uploads Candidate Model.
8. System evaluates Candidate Model on fixed evaluation set and compares to current model.
9. Data Owner promotes or rejects Candidate Model. No auto-promotion occurs.

Alternative flows:
- A1 Re-index failure: system reports failure and keeps previous index state.
- A2 Candidate Model underperforms: Data Owner rejects model; current model remains active.
- A3 Candidate Model improves: Data Owner promotes model; system marks previous version available for rollback/reference.
- A4 No changes: system shows no re-index needed.

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---:|---|---|
| Request | reindex_scope | Conditional | Changed items or full active dataset. | Data Owner only. |
| Request | candidate_model_file | Conditional | Uploaded model artifact. | Valid format/version metadata. |
| Request | promote_decision | Conditional | Promote or reject. | Manual Data Owner decision required. |
| Response | index_status | Yes | Current Qdrant state. | Updated after re-index. |
| Response | retraining_guidance | Conditional | Python instructions for external retraining. | Shown when change threshold reached. |
| Response | evaluation_report | Candidate only | Current vs Candidate Model metrics. | Fixed evaluation set comparison. |

## 8. Non-Functional Requirements

| ID | Requirement | Priority | Stability | Verification |
|---|---|---|---|---|
| NFR-001 | Authentication shall be required for all workflows. | Must | Stable | 401/403 tests |
| NFR-002 | Single retrieval response after segmentation shall complete within 5 seconds under nominal load. | Must | Stable | Performance test |
| NFR-003 | Batch progress state shall become visible within 2 seconds after batch processing starts. | Must | Stable | UI/API test |
| NFR-004 | Uploads shall validate file type, file size, and minimum image dimensions. | Must | Stable | Upload tests |
| NFR-005 | Archived data shall be excluded from retrieval and indexing. | Must | Stable | Query/index tests |
| NFR-006 | All Data Owner mutations shall be audit logged. | Must | Stable | Audit tests |
| NFR-007 | Requirements and use cases shall remain traceable through IDs in this SRS and linked feature/technical specs. | Must | Stable | Documentation review |
| NFR-008 | User-facing terminology shall use canonical terms from `CONTEXT.md`. | Must | Stable | Documentation review |

## 9. Traceability Matrix

| Use Case | Functional Requirements | Existing/Updated Specs |
|---|---|---|
| UC-001 Authenticate User | FR-001 to FR-005 | `feature_spec/08-roles-and-permissions.md`, `technical_spec/11-authentication-authorization.md` |
| UC-002 Retrieve Species | FR-006 to FR-012 | `feature_spec/01-image-input.md`, `02-segmentation.md`, `03-retrieval.md`, `technical_spec/08-retrieval-pipeline.md` |
| UC-003 Submit Feedback | FR-013 to FR-016 | `feature_spec/05-feedback-pipeline.md`, `technical_spec/09-feedback-system.md` |
| UC-004 Index New Data | FR-017, FR-018 | `feature_spec/06-data-management.md`, `technical_spec/06-qdrant-integration.md` |
| UC-005 Manage Metadata | FR-019, FR-020 | `feature_spec/06-data-management.md`, `technical_spec/04-database-design.md` |
| UC-006 Manage Users | FR-003 to FR-005 | `feature_spec/08-roles-and-permissions.md`, `technical_spec/11-authentication-authorization.md` |
| UC-007 Manage Dataset | FR-021 to FR-024, FR-029 | `feature_spec/06-data-management.md`, `technical_spec/04-database-design.md` |
| UC-008 Maintain Model and Index | FR-025 to FR-028 | `feature_spec/07-training-observation.md`, `technical_spec/10-training-pipeline.md` |

## 10. Explicit Rejections and Rationale

| Rejected Idea | Rationale |
|---|---|
| Use **Normal User** as actor name | Creates ambiguity when SRS has exactly two actors. Canonical actor is **User**. |
| Make **Index New Data** include **Retrieve Species** | Bad fit because indexing uses upload/segmentation/bounding-box preparation but bypasses prediction; species metadata is supplied/known. |
| Let User browse reference dataset | Rejected because Users may retrieve and submit feedback but cannot browse or mutate reference dataset. |
| Permanent delete dataset records | Rejected to preserve auditability and retraining/index trace. Use **Archive** only. |
| In-system deep feature-extractor retraining trigger | Rejected; system provides warnings and Python guidance for external retraining/reupload. Qdrant re-indexing remains in-system. |
| Auto-promote Candidate Model | Rejected; Data Owner must assess and manually promote/reject. |
