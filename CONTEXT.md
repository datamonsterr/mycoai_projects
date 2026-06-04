# MycoAI Retrieval

MycoAI Retrieval supports fungal image upload, segmentation, species retrieval, data indexing, and dataset governance for authenticated users.

## Language

**User**:
An authenticated person who retrieves fungal species predictions from uploaded strain images.
_Avoid_: Normal User, researcher

**Data Owner**:
A privileged user responsible for dataset governance, category management, user management, model upload assessment, and indexing new reference data.
_Avoid_: admin, owner, curator

**Batch Template Folder**:
A downloadable folder package that defines the required batch upload structure and includes instructions for restructuring local data before upload.
_Avoid_: template, sample folder

**Image Metadata**:
Species, strain, media, and related descriptive fields attached to an uploaded fungal image.
_Avoid_: label, category

**Species**:
A managed metadata value identifying the fungal taxon associated with reference data or predicted by retrieval.
_Avoid_: species label, class

**Media**:
A managed metadata value identifying the growth medium used for a fungal image.
_Avoid_: media label, environment

**Strain**:
Image metadata identifying the fungal isolate represented by one or more uploaded images.
_Avoid_: strain label, category

**Feedback**:
A user-submitted correction, issue report, or contribution proposal from retrieval results that a Data Owner reviews before any database change is applied.
_Avoid_: change request, report

**Archive**:
A reversible removal state that excludes data from retrieval/indexing without permanently deleting it.
_Avoid_: delete, trash, remove

**Candidate Model**:
An uploaded model version awaiting assessment against a fixed evaluation set before promotion.
_Avoid_: uploaded model, new model

**Data Update Status**:
A dataset item state indicating whether indexed data is current, changed and requiring re-indexing, or archived.
_Avoid_: sync status, dirty flag

## Relationships

- A **Data Owner** has all capabilities of a **User** plus governance capabilities.
- **User** accounts may be created by self-registration or invitation; the initial **Data Owner** is provisioned internally by script using user email, and later role changes may be managed by **Data Owner** role promotion.
- A **User** can retrieve species predictions but cannot browse or mutate the reference dataset.
- A **User** may submit **Feedback** after single or batch retrieval results only, either to report a wrong prediction or propose the retrieved data as a database contribution.
- Accepted contribution **Feedback** becomes pending reference data; a **Data Owner** reviews metadata and bounding boxes before indexing.
- Qdrant re-indexing may be triggered in-system by **Data Owner** after reference-data changes.
- Deep feature-extractor retraining is not triggered by the system; the system warns **Data Owner** when reference-data changes accumulate and provides guidance for external retraining and model reupload.
- A **Candidate Model** is assessed against a fixed evaluation set and must be promoted by a **Data Owner** before replacing the current model.
- Data Owner edits to image metadata mark the item with **Data Update Status** `updated_requires_reindex` and show a re-index warning.
- A **Data Owner** may use batch upload for retrieval or indexing; indexing requires species metadata.
- Retrieval for known **Media** compares against reference images from the same **Media** by default.
- Retrieval for new or other **Media** compares against all available **Media** and flags the **Media** for Data Owner review.
- A **Data Owner** can accept a new **Media** value into the managed list or map it to an existing **Media** value.
- A **Data Owner** can map a free-text suggested species from **Feedback** to an existing **Species** or create a new **Species** during review.
- Both **User** and **Data Owner** can adjust bounding boxes before retrieval or indexing; only **Data Owner** indexing changes the reference dataset.

## Example dialogue

> **Dev:** "Can a **User** index new reference data after segmentation?"
> **Domain expert:** "No — only a **Data Owner** can index reference data; a **User** can run retrieval on uploaded images."

## Flagged ambiguities

- "Normal User" was used in existing docs, while the SRS request uses "User" — resolved: **User** is canonical.
- "Index New Data includes Retrieval" was proposed, but rejected because indexing uses the same preparation workflow while bypassing species prediction; resolved: **Index New Data** includes **Prepare Segmented Images (UC-PREP-01)** and **Submit Reference Dataset**, not **Retrieve Species**.
