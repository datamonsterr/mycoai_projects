# Research Protocol

## Confirmed protocol

- Closed-set benchmark: leave-one-strain-out evaluation
- Open-set benchmark: two separate tracks
  - unseen-strain track
  - unseen-species track
- Missing or new Media at query time: use available Media only
- Retrieval output for scientist-facing research version:
  - species ranking
  - unknown threshold decision
  - per-Media and per-segment evidence
- Threshold objective: maximize unknown detection subject to minimum known-accuracy constraint
- Feature extractor order:
  - traditional baseline
  - pretrained deep baseline
  - finetuned deep model
- Add full-image baseline with no segmentation as an explicit comparison track

## Hard leakage bans

1. Held-out test strain must never appear in fine-tuning training data for same fold.
2. Benchmark retrieval must never use a Qdrant query image that belongs to held-out test strain already stored in database.
3. Benchmark retrieval must run fresh query path:
   - preprocess
   - segment or full-image baseline
   - extract features
   - search Qdrant with held-out strain excluded
4. Historical results are not trusted as evidence until rerun under this protocol.

## Confirmation gates

- Gate A: protocol + audit report
- Gate B: segmentation review bundle
- Gate C: full-image vs segmented comparison
- Gate D: retrieval evidence bundle
- Gate E: threshold behavior bundle
- Gate F: backend/frontend adoption
- Gate G: commit/push for each verified phase

Every gate must include:
- exact folder to inspect
- what right/wrong means
- explicit user confirmation request before continuing

## Required artifacts per major experiment

Each major experiment phase must write artifacts under `results/`:

- raw per-case CSV
- per-strain summary CSV
- visual evidence folders
- charts and diagrams
- machine-readable metadata/config JSON
- short markdown insight summary
- zip archive for upload handoff

## Experiment order

1. Research audit
2. Segmentation validation
3. Full-image baseline
4. Hand-crafted retrieval benchmark
5. Pretrained retrieval benchmark
6. Finetuned retrieval benchmark
7. Open-set threshold benchmark
8. Best-method product handoff
9. Graduation report refresh
