# Manual Test: Feedback Workflow

## Preconditions
- Auth token from owner and regular user
- At least one image with segments exists

### 5.1 Submit Feedback (User)
1. `POST /api/v1/feedback` with:
   ```json
   {
     "image_id": "<image_id>",
     "segment_index": 0,
     "feedback_type": "wrong_prediction",
     "description": "Should be Aspergillus not Penicillium",
     "correct_species_id": "<species_id>"
   }
   ```
2. Expect `201 Created`, `status: "pending"`, `source: "retrieval_result"`

### 5.2 List Feedback (Any Auth)
1. `GET /api/v1/feedback`
2. Expect `200 OK`, paginated

### 5.3 Review Feedback (Owner/Dataowner)
1. `PATCH /api/v1/feedback/{feedback_id}` with `{"status":"accepted"}`
2. Expect `200 OK`, status updated, `reviewed_by` set

### 5.4 Reject Feedback
1. `PATCH /api/v1/feedback/{feedback_id}` with `{"status":"rejected"}`
2. Expect `200 OK`

### 5.5 Batch Update Feedback
1. `POST /api/v1/feedback/batch` with `{"feedback_ids":["id1","id2"],"status":"accepted"}`
2. Expect `200 OK`, all updated

### 5.6 Feedback Integrity
1. Verify feedback linked to correct image and segment
2. Verify `submitter` and `reviewer` user relationships populated
