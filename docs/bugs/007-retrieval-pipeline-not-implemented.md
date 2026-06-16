# Bug 007: Retrieval pipeline not implemented in backend

**Status:** CONFIRMED | **Severity:** High | **Component:** Backend

## Root Cause

`backend/.../api/retrieval.py` entirely returns hardcoded fake data. No Qdrant queries, no feature extraction, no species aggregation in the actual API response path.

**Research has (canonical pipeline in `research/src/experiments/retrieval/run.py`):**

| Capability | Research | Backend | Gap |
|---|---|---|---|
| Qdrant segment query | `find_nearest_neighbors_by_id` | not called | MISSING |
| Per-segment querying | per-segment queries | not implemented | MISSING |
| Sibling filtering | `filter_siblings` | not implemented | MISSING |
| Species aggregation | weighted/uni/manual | partial, unused | WIRING |
| Multi-extractor ensemble | ensemble_analysis.py | not implemented | MISSING |
| Strain mapping | CSV loading | not implemented | MISSING |
| Feature extraction | CNN models | index.py has it | PARTIAL |
| Environment filtering | E1-E4 strategies | not implemented | MISSING |

**Backend retrieval.py stubs:**
- `start_query` (line 16): Creates stub job, never processes
- `get_job_results` (line 46): Returns hardcoded "Penicillium commune" / "DTO 148-D1"
- `query_sync` (line 76): Same hardcoded results

**Backend has partial infrastructure:**
- `qdrant/aggregation.py` — has `aggregate_predictions` with strategies, but never called
- `qdrant/operations.py` — has Qdrant query methods, unused by retrieval API
- `services/feature_extraction.py` — feature extraction available

## Solution

Reimplement retrieval pipeline per `backend-reimplementation.md` rule (reimplement, don't import from research):

1. **Query image** → use existing `extract_features` to get vectors
2. **Segment-level queries** → per-segment Qdrant `search` via `operations.py`
3. **Sibling filtering** → exclude same-parent-image neighbors via `filter_siblings`
4. **Species aggregation** → wire existing `qdrant/aggregation.py` strategies
5. **Environment filtering** → use Qdrant filter on media/environment metadata
6. **Return real rankings** with neighbor details (strain, species, similarity, thumbnail)

## Files to Modify

- `backend/src/mycoai_retrieval_backend/api/retrieval.py` — replace stubs with real pipeline
- `backend/src/mycoai_retrieval_backend/services/retrieval.py` — new orchestration layer
- `backend/src/mycoai_retrieval_backend/qdrant/aggregation.py` — verify/align with research logic
- `backend/src/mycoai_retrieval_backend/qdrant/operations.py` — expose filtered neighbor queries
