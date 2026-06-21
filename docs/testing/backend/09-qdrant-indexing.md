# Manual Test: Qdrant Indexing

## Preconditions
- Qdrant running
- Images with segments exist in database
- Auth token from owner

### 9.1 Check Index Status
1. `GET /api/v1/index/status`
2. Expect: `points_count`, `collections`, `is_initialized` fields

### 9.2 Trigger Full Reindex
1. `POST /api/v1/index/reindex` with `{"scope":"full_active"}`
2. Expect `202 Accepted`, job started
3. Poll `GET /api/v1/index/status` until `is_indexing: false`

### 9.3 Verify Points in Qdrant
1. After reindex, check `points_count` increased
2. `GET /api/v1/index/status` → `indexed_points` matches image segments count

### 9.4 Search After Index
1. Run retrieval query (see 06-retrieval-search.md)
2. Verify results returned with meaningful similarity scores

### 9.5 Delete Image → Index Update
1. Delete an image via API
2. Wait for async reindex or trigger manual
3. Verify point removed from Qdrant (points_count decreased)

### 9.6 Model Info
1. `GET /api/v1/index/models`
2. Expect list of available embedding models with status

### 9.7 Qdrant Collections
1. Direct Qdrant check: `curl http://localhost:6333/collections`
2. Verify expected collections exist

### 9.8 Concurrent Reindex
1. Trigger two reindex requests quickly
2. Expect second request to be queued or rejected gracefully (not duplicate)
