# Feature Spec: Feedback Pipeline

## Overview

Users can report incorrect species predictions. Data owners review, accept,
or reject feedback. Accepted feedback feeds back into model improvement.

## User Stories

### 1. Submit Feedback

**As a** researcher
**I want** to flag incorrect species predictions with a description
**So that** the data owner can review and correct the database

**Behavior:**
- From the results view, user clicks "Report incorrect" on a prediction
- Feedback form:
  - Predicted species (auto-filled)
  - Correct species (dropdown of known species, or "other" with free text)
  - Description (free text, required)
  - Optional: upload supporting image
- Submitted feedback is timestamped and linked to the query strain
- User can view their submitted feedback history

### 2. Review Feedback (Data Owner)

**As a** data owner
**I want** to review submitted feedback
**So that** I can improve the database quality

**Behavior:**
- Data owner inbox: list of pending feedback items
- Each item shows:
  - Submitter info (user ID, timestamp)
  - Query strain, predicted species, suggested correction
  - Description
  - Link to original query results
- Actions per item:
  - **Accept**: update the strain's species in the database
  - **Reject**: record rejection with optional reason
  - **Defer**: leave pending for later review
- Bulk accept/reject with checkbox selection
- Filter by: status, submitter, date range, species

### 3. Feedback on Existing Database Entries

**As a** researcher
**I want** to report issues with existing database entries
**So that** I can flag mislabeled reference data

**Behavior:**
- From any database entry view, user can click "Report issue"
- Same feedback form as above
- Pre-populated with current species/strain data
- Tracked separately from query-result feedback (source = "database_review"
  vs "query_result")

### 4. Database Update on Feedback Acceptance

**As a** data owner
**I want** accepted feedback to update the database
**So that** corrections take effect

**Behavior:**
- On Accept: strain species is updated in the database
- Affected Qdrant points are flagged for re-indexing
- User is notified when their feedback is accepted/rejected
- Audit log records all feedback actions

## Data Contract

**Feedback submission:**

    {
      "feedback_id": "uuid",
      "source": "query_result | database_review",
      "query_strain": "string",
      "predicted_species": "string",
      "suggested_species": "string",
      "description": "string",
      "submitter_id": "uuid",
      "status": "pending | accepted | rejected",
      "created_at": "ISO8601",
      "reviewed_at": "ISO8601 | null",
      "reviewed_by": "uuid | null",
      "review_note": "string | null"
    }

## Acceptance Criteria

- [ ] Feedback form accessible from results view
- [ ] Correct species dropdown with known species + "other" option
- [ ] Required description field
- [ ] Data owner inbox with pending/accept/reject workflow
- [ ] Bulk actions (accept/reject multiple)
- [ ] Feedback on existing database entries
- [ ] Notification on feedback status change
- [ ] Audit log of all feedback actions
- [ ] Qdrant re-indexing trigger on acceptance

## Open Questions

1. Can normal users submit feedback on database entries directly, or only
   through query results? (Spec says "yes" — confirmed)
2. Is re-training automatic on acceptance, or does data owner trigger it
   manually? (See 07-training-observation.md)
3. Should rejected feedback be visible to the submitter?

## Dependencies

- 03-retrieval.md (results view for feedback trigger)
- 04-visualization.md (UI entry point)
- 06-data-management.md (database update on accept)
- 07-training-observation.md (re-training trigger)
- 08-roles-and-permissions.md (data owner permissions)
