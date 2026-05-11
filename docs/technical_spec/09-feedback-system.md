# Technical Spec: Feedback System

## Overview

Design the feedback submission, review, and application pipeline. Feedback
flows from user submissions through data owner review to database updates.

---

## Data Model

See 04-database-design.md for the feedback table schema.

## Submission Flow

    1. User views retrieval results
    2. User clicks "Report incorrect" on a species prediction
    3. Modal/dialog opens with pre-filled form
    4. User selects correct species from dropdown (or "other")
    5. User enters required description
    6. Optional: upload supporting image
    7. Submit -> POST /api/v1/feedback
    8. Show confirmation toast
    9. Feedback appears in user's "My Feedback" list

## Review Flow (Data Owner)

    1. Data owner opens /feedback/inbox
    2. Sees list of pending feedback, sorted by date (newest first)
    3. Each item shows: submitter, query strain, predicted vs suggested,
       description, link to original results
    4. Actions:
       - Accept: modal with optional review note -> PATCH status=accepted
       - Reject: modal with required review note -> PATCH status=rejected
       - Defer: stays pending, optionally add note
    5. Bulk actions: select multiple, accept/reject all
    6. Accepted feedback triggers downstream actions (see below)

## On Accept: Database Update

When data owner accepts feedback:

    1. Update strain species (if strain exists)
       - Update strains.species_id -> new species
       - If suggested species is new ("other"), prompt data owner to
         create the species first
    2. Flag affected Qdrant points for re-indexing
       - Query segments where image.strain_id = feedback strain
       - Update qdrant_index_state.is_active = FALSE
       - Queue Celery task to re-extract + re-upsert
    3. Notify submitter (in-app + optional email)
    4. Log to audit_log

## On Reject: Record Only

    1. Record rejection with required review note
    2. Notify submitter with review note
    3. No database changes
    4. Submitter can see rejection reason in "My Feedback"

## Feedback on Database Entries

Separate from query-result feedback:

    1. User browses database (/database)
    2. User opens a strain/image detail
    3. User clicks "Report issue"
    4. Form: current species (auto-filled), suggested correction,
       description
    5. source = "database_review"
    6. Same review workflow as above

---

## Notification System

**[DECISION: Notification delivery]**

Choices:
- A) **In-app notification bell + optional email** — bell icon with
  unread count, dropdown of recent notifications. Email for accepted/
  rejected feedback (opt-in). **(Recommended)**
- B) Email only — simpler, no in-app complexity
- C) In-app only, no email — all self-contained
- D) Webhook — for integration with lab systems

**Notification types:**

| Event | Notify |
|-------|--------|
| Feedback submitted | Data owner |
| Feedback accepted | Submitter |
| Feedback rejected | Submitter |
| Training complete | Data owner |
| Training failed | Data owner |

---

## Feedback Statistics

**[DECISION: What feedback metrics to track]**

- [ ] Total feedback submitted (by source type)
- [ ] Acceptance rate (accepted / total reviewed)
- [ ] Average review time (submitted -> reviewed)
- [ ] Most frequently misclassified species
- [ ] Feedback by strain (which strains generate most feedback)

---

## Open Questions (from feature spec)

1. Can normal users submit feedback on database entries directly?
   **Answer: Yes**, source = "database_review". Same form, different entry
   point.
2. Is re-training automatic on acceptance?
   **Answer: No**, data owner manually triggers retraining when enough
   changes accumulate. See 07-training-observation.md.
3. Should rejected feedback be visible to the submitter?
   **Answer: Yes**, with data owner's review note explaining the rejection.
