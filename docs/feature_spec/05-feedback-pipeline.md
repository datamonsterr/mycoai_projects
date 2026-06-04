# Feature Spec: Feedback Pipeline

## Overview

Users can submit feedback from retrieval results. Feedback may report an incorrect species prediction, report a result issue, or propose retrieved data as a contribution to the reference dataset. Data Owners review, accept, reject, or defer feedback. No database change is applied until Data Owner approval.

## User Stories

### 1. Submit Feedback from Retrieval Results

**As a** User
**I want** to flag incorrect retrieval results or propose useful retrieved data
**So that** a Data Owner can improve the reference dataset

**Behavior:**
- From the results view, User clicks "Report incorrect" or "Submit as contribution"
- Feedback form:
  - Feedback type: wrong prediction, issue, contribution
  - Predicted species (auto-filled)
  - Correct species: dropdown of known Species, or free-text suggested species
  - Description (required)
  - Optional supporting image/evidence
- Submitted feedback is timestamped and linked to the retrieval result, query strain, media, images, and segments
- User can view their submitted feedback history
- Users cannot browse the reference dataset to submit feedback from dataset entries

### 2. Review Feedback

**As a** Data Owner
**I want** to review submitted feedback
**So that** I can improve database quality without allowing direct User mutation

**Behavior:**
- Data Owner inbox lists pending feedback items
- Each item shows:
  - Submitter info, timestamp
  - Query strain, media, predicted species, suggested correction/contribution intent
  - Description
  - Link to original retrieval result
  - Uploaded images and reviewed bounding boxes when contribution is proposed
- Actions per item:
  - **Accept**: apply accepted correction or move contribution to pending reference data
  - **Reject**: record rejection with optional reason
  - **Defer**: leave pending for later review
- Bulk accept/reject is supported
- Filter by status, submitter, date range, species, feedback type

### 3. Contribution Acceptance

**As a** Data Owner
**I want** accepted contribution feedback to become pending reference data
**So that** I can review metadata and bounding boxes before indexing

**Behavior:**
- On contribution accept, system creates pending reference data
- Data Owner reviews species, strain, media, images, and bounding boxes
- Data Owner can map free-text suggested species to existing Species or create a new Species
- Data Owner can accept new/other Media into managed Media or map it to existing Media
- Data Owner indexes only after final review

### 4. Database Update on Feedback Acceptance

**As a** Data Owner
**I want** accepted correction feedback to update dataset/index state
**So that** corrections take effect under governance

**Behavior:**
- On correction accept: affected dataset item is updated or marked for review
- Affected Qdrant points are flagged `updated_requires_reindex`
- User is notified when feedback is accepted/rejected
- Audit log records all feedback actions

## Data Contract

**Feedback submission:**

    {
      "feedback_id": "uuid",
      "source": "retrieval_result",
      "feedback_type": "wrong_prediction | issue | contribution",
      "retrieval_result_id": "uuid",
      "query_strain": "string",
      "media": "string",
      "predicted_species": "string",
      "suggested_species": "string | null",
      "description": "string",
      "submitter_id": "uuid",
      "status": "pending | accepted | rejected | deferred",
      "created_at": "ISO8601",
      "reviewed_at": "ISO8601 | null",
      "reviewed_by": "uuid | null",
      "review_note": "string | null"
    }

## Acceptance Criteria

- [ ] Feedback form accessible from retrieval results view
- [ ] Feedback supports wrong prediction, issue, and contribution proposal
- [ ] Correct species dropdown with known Species + free-text suggestion
- [ ] Required description field
- [ ] Data Owner inbox with pending/accept/reject/defer workflow
- [ ] Contribution acceptance creates pending reference data before indexing
- [ ] User cannot submit feedback from reference dataset browsing
- [ ] Notification on feedback status change
- [ ] Audit log of all feedback actions
- [ ] Accepted corrections mark affected data for Qdrant re-indexing

## Dependencies

- 03-retrieval.md (results view for feedback trigger)
- 04-visualization.md (UI entry point)
- 06-data-management.md (database update on accept)
- 07-training-observation.md (re-index/retraining warning)
- 08-roles-and-permissions.md (Data Owner permissions)
- ../SRS.md UC-FEEDBACK-01
