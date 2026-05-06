# Quickstart: Dataset Restructure and Derivation

## Scope
Apply dataset restructure for `repos/fungal-cv-qdrant` and verify all downstream consumers that depend on old flat dataset paths.

## 1. Audit current path assumptions
Run targeted searches before implementation:

```bash
grep -R "segmented_image\|full_image\|Dataset/original\|Dataset/new_data" repos/fungal-cv-qdrant/src repos/fungal-cv-qdrant/README.md
```

## 2. Implement unified preparation flow
Expected work:
- replace split KMeans/YOLO reformat scripts with one canonical preparation entrypoint
- update `src/config.py` to expose renamed source collections and canonical prepared artifact roots
- emit metadata records with exact artifact paths for downstream consumers

Canonical prepare now includes segmentation:
```bash
uv --directory repos/fungal-cv-qdrant run python -m src.prepare.init --limit 5
```

Smoke test with specific method:
```bash
uv --directory repos/fungal-cv-qdrant run python -c "
from src.prepare.dataset import segment_item, run_segmentation
from src.config import WORKSPACE_ROOT
# segment_item runs both kmeans+contour per item
"
```

## 3. Update downstream consumers
Must review at minimum:
- `src/prepare/init.py`
- `src/prepare/checks.py`
- feature extraction generators and helpers
- retrieval and visualization helpers
- training and cross-validation flows
- threshold/diverse-data utilities if still active
- README and sync examples

## 4. Validate locally
Run repo checks from monorepo root:

```bash
uv --directory repos/fungal-cv-qdrant run python -m src.prepare.init --help
uv --directory repos/fungal-cv-qdrant run python -m src.experiments.feature_extraction.generate_features --help
uv --directory repos/fungal-cv-qdrant run python -m src.utils.generate_strain_mapping
uv --directory repos/fungal-cv-qdrant run pytest tests/ -v
uv --directory repos/fungal-cv-qdrant run flake8 src/prepare/
```

Run targeted workflow checks after implementation with real sample subset commands chosen from new unified entrypoint.

If sync examples or scopes change, also run:

```bash
uv run pytest tools/tests/test_dataset_sync.py
uv run python tools/dataset_sync.py plan --direction import --remote mydrive:mycoai-dataset --scope [updated-scope]
```

## 5. Manual verification
Inspect:
- canonical prepared tree under `Dataset/`
- one sample item with both `segments_kmeans/` and `segments_contour/`
- one sample bbox visualization and one pipeline visualization per method
- retrieval/training metadata records to confirm they contain exact segment paths
- updated Drive/Vast.ai sync instructions

## 6. Handoff to tasks
Task breakdown should include:
- config and schema update
- unified preparation entrypoint
- downstream consumer migration
- sync/doc updates
- validation and manual evidence capture
