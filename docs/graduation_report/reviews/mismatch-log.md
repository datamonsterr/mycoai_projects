# Implementation and Evidence Mismatch Log

## Product claim mismatches

### Model training lifecycle
- Thesis implies meaningful system workflow for training and promotion.
- Observed code indicates simplified or placeholder endpoints in `backend/src/backend/api/training.py`.
- Frontend states retraining is external and guidance-based in `frontend/src/pages/ModelIndex.tsx`.
- Action: downgrade claim or implement actual workflow plus tests.

### Candidate model upload
- UI affordance exists.
- End-to-end completed upload/promote path not evidenced in inspected code.
- Action: either implement fully or reframe as planned/prototype capability.

## Conclusion inconsistency
- Conclusion says current segmentation pipeline uses classical CV techniques.
- Chapter 2 and product story select YOLO as deployed or chosen method.
- Action: align conclusion with validated chosen configuration.

## Research presentation mismatches
- Some prose implies stronger result certainty than current interpretation depth supports.
- Action: anchor final wording to rerun results, regenerated charts, and reproducible metrics only.
