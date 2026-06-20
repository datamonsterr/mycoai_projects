# Research Progress

## Protocol reset

This file tracks only experiment phases rerun under the current leakage-safe protocol.
Old results are historical context only and are not treated as confirmed evidence.

## Confirmed protocol

- Closed-set: leave-one-strain-out
- Open-set: separate unseen-strain and unseen-species tracks
- New/missing Media: use available Media only
- Output: ranking + unknown threshold + evidence
- Feature order: traditional → pretrained → finetuned
- Comparison track: full image without segmentation

## Phase ledger

| Phase | Status | Date | Best method | Key metric | Evidence folder | Notes |
|---|---|---|---|---:|---|---|
| Research audit | planned | 2026-06-19 | - | - | `results/research_audit/` | Inventory and leakage risk report |
| Segmentation validation | planned | - | - | - | `results/segmentation_review/` | User confirmation required |
| Full-image baseline | planned | - | - | - | `results/full_image_baseline/` | Compare against segmented pipeline |
| Hand-crafted retrieval | planned | - | - | - | `results/retrieval_handcrafted/` | Leakage-safe rerun |
| Pretrained retrieval | planned | - | - | - | `results/retrieval_pretrained/` | Leakage-safe rerun |
| Finetuned retrieval | planned | - | - | - | `results/retrieval_finetuned/` | Fold-safe training required |
| Open-set threshold | planned | - | - | - | `results/openset_threshold/` | Separate tracks |
| Product handoff | planned | - | - | - | `results/product_handoff/` | Backend/frontend only after confirmation |

## Verification rule

No phase may be marked confirmed until:
- artifacts exist
- local checks pass
- user reviews requested evidence bundle
- user explicitly confirms continue
