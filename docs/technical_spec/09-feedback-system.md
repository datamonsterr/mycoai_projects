# Technical Spec: Feedback System

## Overview

Design feedback submission, review, and application pipeline. Feedback flows from retrieval-result submissions through Data Owner review to database updates, pending reference data, or rejection. Users cannot submit feedback from reference dataset browsing.

---

## Data Model

See 04-database-design.md for feedback table schema.

## Submission Flow

    1. User views retrieval results
    2. User clicks "Report incorrect" or "Submit as contribution"
    3. Modal/dialog opens with pre-filled retrieval context
    4. User selects feedback type:
       - wrong_prediction
       - issue
       - contribution
    5. User selects known Species or enters free-text suggested species when relevant
    6. User enters required description
    7. Optional: upload supporting image/evidence
    8. Submit -> POST /api/v1/feedback
    9. Show confirmation
    10. Feedback appears in user's "My Feedback" list

## Review Flow (Data Owner)

    1. Data Owner opens /feedback/inbox
    2. Sees list of pending feedback, sorted by date
    3. Each item shows submitter, query strain, media, predicted vs suggested species,
       feedback type, description, images/segments, link to original results
    4. Actions:
       - Accept: modal with optional review note
       - Reject: modal with required review note
       - Defer: stays pending, optionally add note
    5. Bulk actions: select multiple, accept/reject all
    6. Accepted feedback triggers downstream actions by type

## On Accept: Wrong Prediction or Issue

    1. Data Owner maps suggested species:
       - existing Species, or
       - create new Species first
    2. Update affected dataset item if applicable
    3. Mark affected item Data Update Status = updated_requires_reindex
    4. Notify submitter
    5. Log audit event

## On Accept: Contribution

    1. Create pending reference data from retrieval result images/segments
    2. Data Owner reviews Species, strain, Media, and bounding boxes
    3. If Media is new/other:
       - accept new Media into managed list, or
       - map to existing Media
    4. If suggested species is free text:
       - map to existing Species, or
       - create new Species
    5. Data Owner indexes after final review
    6. Mark new indexed data current or updated_requires_reindex depending index action
    7. Notify submitter
    8. Log audit event

## On Reject: Record Only

    1. Record rejection with required review note
    2. Notify submitter with review note
    3. No database changes
    4. Submitter can see rejection reason in "My Feedback"

---

## Explicit Non-Scope

Users cannot browse the reference dataset and cannot submit feedback from database entry pages. Feedback source is retrieval results only.

---

## Notification System

**Decision: In-app notification bell + optional email.**

| Event | Notify |
|-------|--------|
| Feedback submitted | Data Owner |
| Feedback accepted | Submitter |
| Feedback rejected | Submitter |
| Contribution moved to pending reference data | Data Owner |
| New/other Media pending review | Data Owner |
| Re-index recommended | Data Owner |
| External retraining recommended | Data Owner |

---

## Feedback Statistics

Track:

- Total feedback submitted by type
- Acceptance rate
- Average review time
- Most frequently misclassified Species
- Contribution acceptance count
- New/other Media review count

---

## Resolved Decisions

1. Users submit feedback only from retrieval results.
2. Contribution proposal is feedback type, not direct dataset mutation.
3. Accepted contribution becomes pending reference data before indexing.
4. Accepted correction marks affected data for Qdrant re-indexing.
5. Retraining is not automatic; external retraining guidance is shown when changes accumulate.
