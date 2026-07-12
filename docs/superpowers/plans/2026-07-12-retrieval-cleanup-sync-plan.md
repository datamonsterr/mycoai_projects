# Remaining retrieval cleanup + sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining MycoAI retrieval work by adding safe source-cleanup behavior, wiring delete-impact warnings into product contracts, fixing any residual retrieval drift, and validating research→product sync and dashboard consistency.

**Architecture:** Keep the current upload/retrieval contracts stable and add cleanup as an explicit opt-in capability instead of silently deleting source images behind existing preview endpoints. Reuse the new backend integration tests, extend them with cleanup and sync verification, and add one thin sync path from research artifacts into product SQL/Qdrant/MinIO with dry-run protection first.

**Tech Stack:** FastAPI + SQLAlchemy + Qdrant + MinIO-compatible storage + uv + pytest, React 19 + Vite + TypeScript + Vitest + Testing Library, research feature generation scripts under `research/src/experiments/feature_extraction/`.

---

## File map

- Modify: `backend/src/backend/routes.py`
- Modify: `backend/src/backend/api/media.py`
- Modify: `backend/src/backend/api/species.py`
- Modify: `backend/src/backend/api/strains.py`
- Modify: `backend/src/backend/repos/media.py`
- Modify: `backend/src/backend/repos/species.py`
- Modify: `backend/src/backend/services/storage.py`
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/qdrant/aggregation.py`
- Modify: `backend/scripts/sync_qdrant_to_sql.py`
- Add: `backend/scripts/sync_research_yolo_to_product.py`
- Modify: `backend/tests/test_delete_impacts.py`
- Add: `backend/tests/test_source_cleanup.py`
- Add: `backend/tests/test_sync_research_yolo_to_product.py`
- Modify: `backend/tests/routes/test_retrieval.py`
- Modify: `backend/tests/routes/test_images.py`
- Modify: `backend/tests/integration/test_integration_upload_full.py`
- Modify: `backend/tests/integration/test_integration_e2e_retrieval.py`
- Modify: `frontend/src/pages/Metadata.tsx`
- Modify: `frontend/src/services/media.ts`
- Modify: `frontend/src/services/species.ts`
- Modify: `frontend/src/services/strains.ts`
- Add: `frontend/src/__tests__/metadata-delete-impact.test.tsx`

## Dependency graph

1. Cleanup contract tests
2. Cleanup backend implementation
3. Delete-impact frontend wiring
4. Retrieval residual bug tests
5. Retrieval residual fixes
6. Research→product sync dry-run tests
7. Sync implementation + execution
8. Dashboard/API verification
9. Final validation + manual checks

### Task 1: Add failing cleanup contract tests

**Files:**
- Add: `backend/tests/test_source_cleanup.py`
- Modify: `backend/tests/test_delete_impacts.py`
- Modify: `backend/tests/routes/test_images.py`

- [ ] **Step 1: Write a failing backend cleanup unit test**

```python
@pytest.mark.asyncio
async def test_cleanup_source_removes_source_object_after_segment_success(session, client, headers):
    response = client.post(
        "/api/v1/images/<image_id>/cleanup-source",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["source_removed"] is True
```

- [ ] **Step 2: Write a failing source retrieval regression test**

```python
def test_source_endpoint_returns_410_after_cleanup(client, headers, image_id):
    cleanup = client.post(f"/api/v1/images/{image_id}/cleanup-source", headers=headers)
    assert cleanup.status_code == 200
    source = client.get(f"/api/v1/images/{image_id}/source", headers=headers)
    assert source.status_code == 410
```

- [ ] **Step 3: Extend delete-impact tests to assert archive warning details**

```python
assert body["image_count"] == 1
assert body["warning_message"].startswith("Archiving this")
```

- [ ] **Step 4: Run cleanup-focused tests to confirm RED**

Run:
```bash
uv --directory backend run pytest tests/test_source_cleanup.py tests/test_delete_impacts.py tests/routes/test_images.py -q
```

Expected: FAIL with missing `/cleanup-source` route and missing `warning_message` fields.

### Task 2: Implement source cleanup endpoint safely

**Files:**
- Modify: `backend/src/backend/routes.py`
- Modify: `backend/src/backend/services/storage.py`
- Add: `backend/tests/test_source_cleanup.py`

- [ ] **Step 1: Add an explicit cleanup response payload**

```python
from pydantic import BaseModel

class SourceCleanupResponse(BaseModel):
    image_id: str
    source_removed: bool
    source_path: str
```

- [ ] **Step 2: Add a helper that deletes only the persisted source artifact**

```python
def _delete_source_artifact(storage: ObjectStorage | None, artifact_dir: Path) -> bool:
    key = f"{artifact_dir}/source.jpg"
    if storage is not None and storage.object_exists(key):
        storage.delete(key)
        return True
    local_path = (artifact_dir / "source.jpg") if artifact_dir.is_absolute() else Path("Dataset/uploads") / artifact_dir / "source.jpg"
    if local_path.exists():
        local_path.unlink()
        return True
    return False
```

- [ ] **Step 3: Add `POST /api/v1/images/{image_id}/cleanup-source`**

```python
@router.post("/{image_id}/cleanup-source", response_model=SourceCleanupResponse)
async def cleanup_image_source(...):
    img = await _get_image_for_update(db, image_id)
    if not img.segments:
        raise HTTPException(status_code=409, detail="cannot cleanup source before segmentation")
    removed = _delete_source_artifact(storage, Path(img.file_path).parent)
    return SourceCleanupResponse(image_id=str(img.id), source_removed=removed, source_path=str(Path(img.file_path).parent / "source.jpg"))
```

- [ ] **Step 4: Make source endpoint return 410 when source was explicitly cleaned**

```python
if not local_path.exists():
    raise HTTPException(status_code=410, detail="source image was cleaned after segmentation")
```

- [ ] **Step 5: Re-run cleanup tests to verify GREEN**

Run:
```bash
uv --directory backend run pytest tests/test_source_cleanup.py tests/test_delete_impacts.py tests/routes/test_images.py -q
```

Expected: PASS

### Task 3: Add warning messages to delete-impact APIs

**Files:**
- Modify: `backend/src/backend/schemas/delete_impact.py`
- Modify: `backend/src/backend/api/media.py`
- Modify: `backend/src/backend/api/species.py`
- Modify: `backend/src/backend/api/strains.py`

- [ ] **Step 1: Extend schema with explicit warning text**

```python
class DeleteImpactResponse(BaseModel):
    image_count: int
    strain_count: int = 0
    warning_message: str
```

- [ ] **Step 2: Add media warning text**

```python
return DeleteImpactResponse(
    image_count=image_count,
    warning_message=f"Archiving this media affects {image_count} image(s).",
)
```

- [ ] **Step 3: Add species warning text**

```python
return DeleteImpactResponse(
    image_count=image_count,
    strain_count=strain_count,
    warning_message=f"Archiving this species affects {strain_count} strain(s) and {image_count} image(s).",
)
```

- [ ] **Step 4: Add strain warning text**

```python
return DeleteImpactResponse(
    image_count=image_count,
    warning_message=f"Archiving this strain affects {image_count} image(s).",
)
```

- [ ] **Step 5: Run delete-impact tests**

Run:
```bash
uv --directory backend run pytest tests/test_delete_impacts.py -q
```

Expected: PASS

### Task 4: Wire frontend metadata warnings

**Files:**
- Modify: `frontend/src/services/media.ts`
- Modify: `frontend/src/services/species.ts`
- Modify: `frontend/src/services/strains.ts`
- Modify: `frontend/src/pages/Metadata.tsx`
- Add: `frontend/src/__tests__/metadata-delete-impact.test.tsx`

- [ ] **Step 1: Add failing frontend service tests for delete-impact endpoints**

```ts
const result = await media.getDeleteImpact('media-1')
expect(result.image_count).toBe(3)
```

- [ ] **Step 2: Add failing Metadata page test for warning dialog content**

```tsx
expect(await screen.findByText(/affects 2 strain\(s\) and 8 image\(s\)/i)).toBeInTheDocument()
```

- [ ] **Step 3: Add typed service helpers**

```ts
export type DeleteImpact = { image_count: number; strain_count?: number; warning_message: string }
```

- [ ] **Step 4: Fetch delete-impact before archive action and show confirm dialog**

```tsx
const impact = await species.getDeleteImpact(id)
setPendingArchive({ type: 'species', id, impact })
```

- [ ] **Step 5: Run frontend warning tests**

Run:
```bash
pnpm --dir frontend test -- src/__tests__/metadata-delete-impact.test.tsx src/__tests__/services.test.ts
```

Expected: PASS

### Task 5: Reproduce remaining retrieval drift

**Files:**
- Modify: `backend/tests/routes/test_retrieval.py`
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/qdrant/aggregation.py`

- [ ] **Step 1: Add failing batch strain-label test**

```python
assert response["strain"] == "batch"
```

- [ ] **Step 2: Add failing freq-strength aggregation parity test**

```python
assert ranking[0]["species"] == "Penicillium chrysogenum"
assert ranking[0]["score"] > ranking[1]["score"]
```

- [ ] **Step 3: Run targeted retrieval RED suite**

Run:
```bash
uv --directory backend run pytest tests/routes/test_retrieval.py tests/test_weights_parity.py -q
```

Expected: FAIL on current residual drift.

### Task 6: Fix retrieval residual bugs

**Files:**
- Modify: `backend/src/backend/api/retrieval.py`
- Modify: `backend/src/backend/qdrant/aggregation.py`

- [ ] **Step 1: Use explicit batch strain label when `image_ids` contains more than one image**

```python
job_strain_name = primary_strain_name if len(query_images) == 1 else "batch"
```

- [ ] **Step 2: Keep queried image neighbor rows per uploaded image, not first-image-only summary**

```python
queried_images.append({...})
```

- [ ] **Step 3: Ensure `freq_strength` math stays aligned with integration expectations**

```python
strength = total_score / count if count > 0 else 0.0
final = freq * strength
```

- [ ] **Step 4: Re-run retrieval suite**

Run:
```bash
uv --directory backend run pytest tests/routes/test_retrieval.py tests/integration/test_integration_e2e_retrieval.py -q
```

Expected: PASS

### Task 7: Add dry-run sync verification tests

**Files:**
- Add: `backend/tests/test_sync_research_yolo_to_product.py`
- Modify: `backend/scripts/sync_qdrant_to_sql.py`
- Add: `backend/scripts/sync_research_yolo_to_product.py`

- [ ] **Step 1: Write a failing sync script test for dry-run reporting**

```python
def test_sync_research_yolo_to_product_dry_run_reports_counts(tmp_path):
    result = run_sync(..., dry_run=True)
    assert result["would_upsert_images"] >= 0
```

- [ ] **Step 2: Write a failing sync script test for MinIO path verification**

```python
assert result["missing_segment_objects"] == []
```

- [ ] **Step 3: Run sync RED tests**

Run:
```bash
uv --directory backend run pytest tests/test_sync_research_yolo_to_product.py -q
```

Expected: FAIL because script does not exist yet.

### Task 8: Implement research→product sync script

**Files:**
- Add: `backend/scripts/sync_research_yolo_to_product.py`
- Modify: `backend/scripts/sync_qdrant_to_sql.py`

- [ ] **Step 1: Build a minimal dry-run CLI**

```python
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--features-json", type=Path, required=True)
```

- [ ] **Step 2: Read `/tmp/opencode/segmented_features_effb1_test.json` or supplied features JSON and group by image/strain/species/media**

```python
with args.features_json.open() as handle:
    rows = json.load(handle)
```

- [ ] **Step 3: Verify SQL metadata + object storage presence before write mode**

```python
result["missing_segment_objects"].append(segment_path)
```

- [ ] **Step 4: Reuse existing SQL upsert helpers where possible; keep writes idempotent**

```python
if args.dry_run:
    return report
```

- [ ] **Step 5: Run sync tests and one manual dry-run**

Run:
```bash
uv --directory backend run pytest tests/test_sync_research_yolo_to_product.py -q
uv --directory backend run python scripts/sync_research_yolo_to_product.py --features-json /tmp/opencode/segmented_features_effb1_test.json --dry-run
```

Expected: tests PASS, CLI prints counts only.

### Task 9: Verify dashboard and product counts

**Files:**
- None or small fixes in backend dashboard endpoints

- [ ] **Step 1: Record current dataset counts from `Dataset/original_prepared`**

Run:
```bash
python - <<'PY'
from pathlib import Path
root = Path('Dataset/original_prepared')
print(sum(1 for _ in root.glob('*/*/*/*/segments_yolo/segment_*.jpg')))
PY
```

- [ ] **Step 2: Record current backend dashboard values**

Run:
```bash
curl -sf http://localhost:8000/api/v1/dashboard/stats
curl -sf http://localhost:8000/api/v1/dashboard/qdrant-status
```

- [ ] **Step 3: If counts drift, add a focused backend test first, then fix endpoint logic**

### Task 10: Final validation

**Files:**
- Any touched above

- [ ] **Step 1: Run backend validation**

Run:
```bash
uv --directory backend run ruff check .
uv --directory backend run mypy src tests/test_delete_impacts.py tests/test_source_cleanup.py tests/test_sync_research_yolo_to_product.py tests/integration/test_integration_yolo_seg.py tests/integration/test_integration_feature_parity.py tests/integration/test_integration_upload_full.py tests/integration/test_integration_e2e_retrieval.py
uv --directory backend run pytest tests/test_delete_impacts.py tests/test_weights_parity.py tests/integration/test_integration_yolo_seg.py tests/integration/test_integration_feature_parity.py tests/integration/test_integration_upload_full.py tests/integration/test_integration_e2e_retrieval.py tests/test_api_media.py tests/test_batch_zip.py tests/routes/test_images.py tests/routes/test_retrieval.py -q
```

Expected: PASS

- [ ] **Step 2: Run frontend validation**

Run:
```bash
pnpm --dir frontend lint
pnpm --dir frontend typecheck
pnpm --dir frontend build
pnpm --dir frontend test -- src/__tests__/retrieve-page.test.tsx src/__tests__/index-new-data.test.tsx src/__tests__/metadata-delete-impact.test.tsx
```

Expected: PASS

- [ ] **Step 3: Manual/API verification**

Run:
```bash
curl -sf http://localhost:8000/api/v1/media
curl -sf http://localhost:8000/api/v1/species
curl -sf http://localhost:8000/api/v1/strains
```

Expected: delete-impact endpoints available, retrieval stack still healthy.
