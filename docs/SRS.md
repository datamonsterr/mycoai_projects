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

(Retrieve Species) ..> (UC-PREP-01\nPrepare Segmented\nImages) : <<include>>
(Index New Data) ..> (UC-PREP-01\nPrepare Segmented\nImages) : <<include>>
(Index New Data) ..> (Manage Metadata) : <<include>>
(Submit Feedback) ..> (Retrieve Species) : <<extend>>
```

Important notes:
- **UC-PREP-01 Prepare Segmented Images** is shared internal behavior, not actor-facing top-level intent.
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
| FR-030 | System shall allow configurable KNN parameter k (1-20) and aggregation strategy (weighted / uni). | User, Data Owner | Should | Evolving | KNN configuration tests |
| FR-031 | System shall support multi-Media queries aggregating images of same strain across multiple Media. | User, Data Owner | Should | Evolving | Multi-media query tests |
| FR-032 | System shall display ranked retrieval results with confidence scores and support results visualization. | User, Data Owner | Must | Stable | Results display tests |
| FR-033 | System shall provide dataset overview dashboard with metrics (total images, strains, species, media types, distributions, index status). | Data Owner | Must | Evolving | Dashboard tests |
| FR-034 | System shall enforce role-based API access returning 403 for Data Owner-only endpoints accessed by Users. | User, Data Owner | Must | Stable | RBAC enforcement tests |

## 7. Use Case Specifications

### UC-AUTH-01 Authenticate User

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Access protected workflows through authenticated session. |
| Preconditions | Account exists, or User self-registers. Initial Data Owner may be provisioned by internal script. |
| Postconditions | Authenticated session established or access denied. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Actor opens authentication screen. | - |
| 2 | Actor registers or logs in with email and password. | - |
| 3 | - | System validates credentials. |
| 4 | - | System establishes session and loads actor role. |
| 5 | - | System routes actor to permitted dashboard. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 | Actor submits invalid credentials. | System rejects login and shows error. |
| A2 | Authenticated actor has inactive account. | System blocks access and shows account status. |
| A3 | Data Owner sends onboarding email. | Recipient completes registration. |
| A4 | - | Internal script assigns Data Owner role to a user email (first Data Owner setup). |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | email | Yes | Actor email address. | Must be valid email format. |
| Request | password | Yes | Actor secret. | Must satisfy password policy. |
| Request | name | Registration only | Display name. | Non-empty. |
| Response | session | Yes | Authenticated session/token state. | Returned only after valid credentials. |
| Response | role | Yes | `user` or `owner`. | Controls UI/API permissions. |
| Error | unauthorized | Conditional | Invalid credentials/session. | Return 401. |
| Error | forbidden | Conditional | Authenticated but unauthorized. | Return 403. |

### UC-RETRIEVE-01 Retrieve Species

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Predict fungal species from uploaded strain images. |
| Includes | UC-PREP-01 Prepare Segmented Images |
| Preconditions | Actor is authenticated. |
| Postconditions | Ranked species predictions are available; batch CSV may be downloaded; actor may submit feedback. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Actor uploads one image or a batch folder. | - |
| 2 | For batch, actor may download Batch Template Folder and use included instructions to restructure local data before upload. | - |
| 3 | Actor provides image metadata: strain and media. Species is not required for retrieval. | - |
| 4 | - | System previews uploaded images and metadata. |
| 5 | - | System invokes UC-PREP-01 Prepare Segmented Images to run auto-segmentation and bounding-box review. |
| 6 | Actor edits/removes bounding boxes if needed (as specified in UC-PREP-01). | - |
| 7 | - | System selects KNN strategy: same-media for managed Media, all-media for new/other Media. |
| 8 | - | System retrieves nearest reference vectors and aggregates predictions across images/segments. |
| 9 | - | System displays ranked species predictions and confidence scores. |
| 10 | For batch, actor downloads batch results CSV. | - |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 New/other Media | - | System uses all-media KNN, flags Media for Data Owner review, and marks prediction context as new/other Media. |
| A2 Invalid upload structure | Actor submits invalid batch structure. | System rejects batch and shows template mismatch. |
| A3 Poor segmentation | Actor manually adjusts boxes before processing (see UC-PREP-01 A1). | - |
| A4 Removed image | Actor removes batch image before processing. | System skips removed image. |
| A5 No valid segment remains | - | System blocks retrieval until at least one segment exists (see UC-PREP-01 A3). |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | images | Yes | Single image or batch folder images. | JPEG/PNG/TIFF, minimum size, max upload size. |
| Request | strain | Yes | Isolate identifier. | Free text, non-empty. |
| Request | media | Yes | Managed Media or new/other Media. | Managed value or flagged free text. |
| Request | max_colonies | No | Max segments per image. | Integer 1-10. |
| Request | bbox_edits | No | Manual box changes. | Must stay within image bounds. |
| Response | predictions | Yes | Ranked species list with scores. | Top results sorted by score. |
| Response | strategy | Yes | Same-media or all-media KNN. | Derived from media status. |
| Response | batch_csv | Batch only | Downloadable result table. | Includes image, strain, media, predicted species, confidence, bbox status, feedback/contribution status. |
| Error | invalid_upload | Conditional | File/folder validation failed. | Show actionable validation message. |

Notes: Data Owner can also retrieve species through inherited User capabilities.

### UC-PREP-01 Prepare Segmented Images

| Field | Value |
|---|---|
| Primary Actor | System (internal); reviewed by User or Data Owner |
| Goal | Produce validated segmented colony crops from uploaded fungal images for retrieval or indexing. |
| Preconditions | Images uploaded; actor authenticated. |
| Postconditions | Segmented colony crops are available; actor may proceed to retrieval (UC-RETRIEVE-01) or indexing (UC-DATA-01). |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | - | System receives uploaded images and metadata from calling workflow. |
| 2 | - | System runs AI auto-segmentation to detect colony regions. |
| 3 | - | System generates bounding boxes and segmented crops for each detected colony. |
| 4 | Actor reviews auto-generated bounding boxes on each image. | - |
| 5 | Actor edits, removes, or adds bounding boxes as needed. | - |
| 6 | - | System validates bounding boxes are within image bounds. |
| 7 | Actor confirms final bounding boxes. | - |
| 8 | - | System produces final segmented colony crops ready for feature extraction. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Poor auto-segmentation | Actor manually adjusts boxes before confirmation. | - |
| A2 No colony detected | - | System warns actor; actor may manually draw bounding boxes. |
| A3 No valid segment remains after removal | - | System blocks retrieval/indexing until at least one valid segment exists. |
| A4 Image removed before confirmation | Actor removes image. | System skips segmentation for removed image. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Input | images | Yes | Uploaded fungal strain images. | Valid image format and dimensions. |
| Input | max_colonies | No | Maximum segments per image. | Integer 1-10. |
| Input | bbox_edits | No | Manual bounding-box adjustments. | Must stay within image bounds. |
| Output | segments | Yes | Validated segment crops with bounding boxes. | At least one valid segment per retained image. |
| Error | no_valid_segment | Conditional | No valid colony segment remains. | Blocks downstream retrieval or indexing. |

### UC-FEEDBACK-01 Submit Feedback

| Field | Value |
|---|---|
| Primary Actor | User, Data Owner |
| Goal | Submit correction, issue report, or contribution proposal from retrieval results. |
| Extends | UC-RETRIEVE-01 Retrieve Species |
| Preconditions | Retrieval result exists. |
| Postconditions | Feedback is pending Data Owner review. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Actor views retrieval result. | - |
| 2 | Actor selects submit feedback or contribute result. | - |
| 3 | - | System pre-fills prediction, strain, media, images, segments, and confidence data. |
| 4 | Actor provides corrected species, free-text suggested species, or contribution intent. | - |
| 5 | Actor submits description and optional supporting evidence. | - |
| 6 | - | System records feedback as pending and notifies Data Owner. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Wrong prediction | Actor selects known Species or enters free-text species suggestion. | - |
| A2 Contribution proposal | Actor confirms retrieved data may be reviewed for database inclusion. | - |
| A3 Batch feedback | Actor submits feedback for one or more batch rows. | - |
| A4 Missing required description | Actor submits without description. | System blocks submission. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | retrieval_result_id | Yes | Source retrieval result. | Must belong to actor or permitted scope. |
| Request | feedback_type | Yes | `wrong_prediction`, `issue`, `contribution`. | Must be valid type. |
| Request | suggested_species | Conditional | Known Species or free text. | Required for wrong prediction when available. |
| Request | description | Yes | Explanation for Data Owner. | Non-empty. |
| Request | supporting_image | No | Additional evidence. | Valid image type/size. |
| Response | feedback_id | Yes | Created feedback identifier. | Status `pending`. |
| Response | status | Yes | Review state. | `pending`, `accepted`, `rejected`, `deferred`. |

### UC-DATA-01 Index New Data

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Add known reference data to retrieval database. |
| Includes | UC-PREP-01 Prepare Segmented Images, UC-META-01 Manage Metadata |
| Preconditions | Data Owner authenticated; Species and Media metadata exist or are created during workflow. |
| Postconditions | Reference images/segments are indexed or staged for Qdrant re-indexing. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Data Owner chooses single or batch indexing. | - |
| 2 | Data Owner uploads images or structured batch folder. | - |
| 3 | Data Owner supplies required metadata: species, strain, media. | - |
| 4 | Data Owner reviews images, metadata, and bounding boxes. | - |
| 5 | - | System invokes UC-PREP-01 Prepare Segmented Images for auto-segmentation. |
| 6 | Data Owner reviews and adjusts bounding boxes (see UC-PREP-01 step 5-6). | - |
| 7 | Data Owner removes unwanted data before submit. | - |
| 8 | - | System stores accepted images/segments as reference data. |
| 9 | - | System indexes data into Qdrant or marks it for re-indexing. |
| 10 | - | System records audit log. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Missing Species/Media | - | Data Owner creates metadata through UC-META-01 Manage Metadata. |
| A2 Batch indexing | Data Owner uploads batch folder. | System reads species metadata from folder structure/template; invokes UC-PREP-01 for batch segmentation. |
| A3 Accepted contribution feedback | - | System presents pending reference data for Data Owner review before indexing (see UC-PREP-01 segmentation + UC-META-01 metadata). |
| A4 Bad bounding box | Data Owner fixes boxes using manual labeling tools (see UC-PREP-01 A1). | - |
| A5 Existing duplicate | - | System warns and requires Data Owner decision. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | images/folder | Yes | Reference images or batch folder. | Valid upload/template structure. |
| Request | species | Yes | Managed Species. | Must exist or be created. |
| Request | strain | Yes | Strain metadata. | Non-empty. |
| Request | media | Yes | Managed Media. | Must exist or be created. |
| Request | bbox_edits | No | Reviewed segment boxes. | Must stay within image bounds. |
| Response | dataset_item_id | Yes | Created/updated dataset item. | Audit logged. |
| Response | index_status | Yes | Qdrant indexing state. | `current` or `updated_requires_reindex`. |
| Error | missing_metadata | Conditional | Required metadata absent. | Prompt create/select metadata. |

### UC-META-01 Manage Metadata

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Maintain Species and Media catalogs used by retrieval/indexing. |
| Preconditions | Data Owner authenticated. |
| Postconditions | Metadata catalog is updated and audited. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Data Owner opens metadata management. | - |
| 2 | Data Owner creates, updates, archives, or restores Species or Media. | - |
| 3 | - | System validates uniqueness and references. |
| 4 | - | System warns if metadata change requires re-indexing. |
| 5 | - | System saves change and records audit log. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 User submitted new/other Media | Data Owner accepts as new Media or maps to existing Media. | - |
| A2 User suggested free-text species | Data Owner maps to existing Species or creates new Species during feedback review. | - |
| A3 Duplicate metadata | Data Owner submits duplicate value. | System blocks duplicate. |
| A4 Metadata in use | - | System warns affected dataset items and Qdrant impact. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | metadata_type | Yes | `species` or `media`. | Strain is not metadata catalog. |
| Request | name | Yes | Metadata display value. | Unique, case-insensitive. |
| Request | description | No | Optional notes. | Stored for Data Owner context. |
| Response | metadata_id | Yes | Created/updated value identifier. | Returned after save. |
| Response | reindex_warning | Conditional | Impact summary. | Shown when references affected. |

### UC-AUTH-02 Manage Users

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Govern system users and roles. |
| Preconditions | Data Owner authenticated. |
| Postconditions | User account or role state is updated and audited. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Data Owner opens user management. | - |
| 2 | Data Owner invites user by onboarding email or reviews existing users. | - |
| 3 | Data Owner activates/deactivates users or promotes/demotes roles. | - |
| 4 | - | System enforces at least one active Data Owner. |
| 5 | - | System records audit log. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Self-registration | User creates account without invite. | - |
| A2 Initial Data Owner | - | Internal script provisions first Data Owner by email. |
| A3 Demote last Data Owner | Data Owner attempts to demote last Data Owner. | System blocks change. |
| A4 Invite already registered email | Data Owner invites existing email. | System shows existing account status. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | email | Yes | Target user email. | Valid email. |
| Request | role | Conditional | `user` or `owner`. | Only Data Owner can change roles. |
| Request | account_status | Conditional | Active/inactive. | Cannot deactivate last Data Owner. |
| Response | user_id | Yes | User identifier. | Updated user returned. |
| Response | onboarding_status | Invite only | Invite state. | Sent, accepted, expired. |

### UC-DATA-02 Manage Dataset

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Browse, update, archive, restore, and govern dataset records. |
| Preconditions | Data Owner authenticated. |
| Postconditions | Dataset state updated; affected items marked for re-index when needed. |
| Priority | Must |
| Stability | Stable |

| Step | Actor | System Response |
|---|---|---|
| 1 | Data Owner opens dataset browser. | - |
| 2 | - | System shows dataset with search, filter, browse, and group by strain/media/species. |
| 3 | Data Owner views images, metadata, segments, and Data Update Status. | - |
| 4 | Data Owner edits metadata or bounding boxes, archives, or restores items. | - |
| 5 | - | System marks changed items as `updated_requires_reindex` when needed. |
| 6 | - | System excludes archived items from retrieval/indexing. |
| 7 | - | System records audit log. |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Archive item | Data Owner archives item. | System marks item archived; no permanent delete exists. |
| A2 Restore item | Data Owner restores item. | System returns item to active state; marks for re-index if needed. |
| A3 Metadata edit after indexing | Data Owner edits indexed metadata. | System warns re-index required. |
| A4 Bulk update/archive | Data Owner selects multiple items. | System shows affected item count and requires confirmation. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
| Request | filters | No | Strain/media/species/date/status filters. | Returns matching dataset rows. |
| Request | group_by | No | `strain`, `media`, `species`. | Groups browser results. |
| Request | metadata_update | Conditional | Species/strain/media edits. | Marks `updated_requires_reindex`. |
| Request | archive_action | Conditional | Archive or restore. | No permanent delete. |
| Response | dataset_items | Yes | Matching data rows. | Data Owner only. |
| Response | data_update_status | Yes | `current`, `updated_requires_reindex`, `archived`. | Drives re-index warnings. |

### UC-MODEL-01 Maintain Model and Index

| Field | Value |
|---|---|
| Primary Actor | Data Owner |
| Goal | Keep Qdrant index and feature-extractor model versions governed. |
| Preconditions | Data Owner authenticated. |
| Postconditions | Qdrant may be re-indexed; Data Owner may receive retraining guidance; Candidate Model may be promoted/rejected. |
| Priority | Must |
| Stability | Evolving |

| Step | Actor | System Response |
|---|---|---|
| 1 | Data Owner opens model/index dashboard. | - |
| 2 | - | System shows current model version, index status, changed data count, archived data count, accepted feedback count, and evaluation metrics. |
| 3 | Data Owner triggers Qdrant re-index for changed reference data when needed. | - |
| 4 | - | System runs re-index and updates index status. |
| 5 | - | If many changes accumulate, system warns Data Owner that external deep feature-extractor retraining is recommended. |
| 6 | - | System provides Python guidance to download dataset, retrain externally, and reupload model. |
| 7 | Data Owner uploads Candidate Model. | - |
| 8 | - | System evaluates Candidate Model on fixed evaluation set and compares to current model. |
| 9 | Data Owner promotes or rejects Candidate Model. No auto-promotion occurs. | - |

Alternative flows:

| Step | Actor | System Response |
|---|---|---|
| A1 Re-index failure | - | System reports failure and keeps previous index state. |
| A2 Candidate Model underperforms | Data Owner rejects model. | Current model remains active. |
| A3 Candidate Model improves | Data Owner promotes model. | System marks previous version available for rollback/reference. |
| A4 No changes | - | System shows no re-index needed. |

Data table:

| Direction | Field | Required | Description | Validation/System Response |
|---|---|---|---:|---|---|
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
| NFR-009 | All API error responses shall follow a consistent JSON structure with `error_code`, `message`, and optional `field_errors`. | Must | Stable | API error format tests |
| NFR-010 | Batch and long-running operations shall support asynchronous processing with status endpoint polling. | Should | Evolving | Async processing tests |
| NFR-011 | Data Owner-only endpoints shall return 403 Forbidden when accessed by Users. | Must | Stable | RBAC tests |
| NFR-012 | JWT tokens shall expire after a configured duration and support token refresh. | Must | Stable | Auth expiration tests |
| NFR-013 | All client-server communication shall use HTTPS in production environments. | Must | Stable | Network configuration check |
| NFR-014 | System shall validate and sanitize all user inputs before processing. | Must | Stable | Input validation tests |
| NFR-015 | Secrets, keys, and credentials shall not appear in logs, error responses, or client-visible output. | Must | Stable | Secret leak detection |

## 9. Explicit Rejections and Rationale

| Rejected Idea | Rationale |
|---|---|
| Use **Normal User** as actor name | Creates ambiguity when SRS has exactly two actors. Canonical actor is **User**. |
| Make **Index New Data** include **Retrieve Species** | Bad fit because indexing uses upload/segmentation/bounding-box preparation but bypasses prediction; species metadata is supplied/known. |
| Let User browse reference dataset | Rejected because Users may retrieve and submit feedback but cannot browse or mutate reference dataset. |
| Permanent delete dataset records | Rejected to preserve auditability and retraining/index trace. Use **Archive** only. |
| In-system deep feature-extractor retraining trigger | Rejected; system provides warnings and Python guidance for external retraining/reupload. Qdrant re-indexing remains in-system. |
| Auto-promote Candidate Model | Rejected; Data Owner must assess and manually promote/reject. |

## 10. Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | 2026-05-15 | MycoAI Team | Initial SRS for MycoAI Retrieval. 8 use cases (UC-001 to UC-008), 29 functional requirements, 8 non-functional requirements, traceability matrix, architecture overview. |
| 2.0.0 | 2026-06-02 | MycoAI Team | UC IDs renamed to module-scoped format (UC-AUTH-01, UC-RETRIEVE-01, UC-FEEDBACK-01, UC-DATA-01, UC-META-01, UC-AUTH-02, UC-DATA-02, UC-MODEL-01). Added UC-PREP-01 Prepare Segmented Images as shared internal use case. All main/alt/exception flows converted to table format (Step, Actor, System Response). Use case diagram updated: UC-PREP-01 node added, auth <<include>> lines removed. New FRs: FR-030 (configurable KNN), FR-031 (multi-media queries), FR-032 (results visualization), FR-033 (dataset dashboard), FR-034 (role-based API enforcement). New NFRs: NFR-009 to NFR-015 (API error format, async processing, Data Owner constraint, JWT expiry, HTTPS, input validation, secret leak prevention). Traceability Matrix removed (links live in feature/tech spec cross-references). Architecture Overview section removed (lives in technical_spec/01-tech-stack.md). UC-RETRIEVE-01 references UC-PREP-01 in main flow steps 5-6. UC-DATA-01 Includes field updated to UC-PREP-01. UC-RETRIEVE-01 Notes added: Data Owner inherits User retrieval capabilities. |
