# Manual Test: Retrieval Search

## Preconditions
- Qdrant running: `docker compose up -d qdrant-product`
- Multiple images indexed (segment vectors in Qdrant)
- Auth token from owner

### 6.1 Search by Image
1. `POST /api/v1/retrieval/query` with:
   ```json
   {
     "image_id": "<image_id>",
     "k": 10,
     "filter": {"environment": "CYA"}
   }
   ```
2. Expect `200 OK`, response contains `status`, `results` array

### 6.2 Verify Result Structure
1. Each result has: `rank`, `score`, `strain_name`, `species_name`, `neighbors`
2. Each neighbor has: `neighbor_image_id`, `similarity`, `strain_name`

### 6.3 Empty Search (No Matches)
1. Query with filter that matches no points
2. Expect `200 OK`, empty `results` array

### 6.4 Search by Point ID
1. `POST /api/v1/retrieval/query` with `{"point_id":"<qdrant_point_id>","k":5}`
2. Expect results excluding self, `exclude_self: true`

### 6.5 Invalid k Value
1. Query with `k: 0` or `k: 200`
2. Expect `422 Unprocessable Entity`

### 6.6 Retrieval Job Status
1. `GET /api/v1/retrieval/jobs`
2. Expect list of past retrieval jobs with `status`, `created_at`

### 6.7 Dashboard Stats
1. `GET /api/v1/dashboard/stats`
2. Expect `total_species`, `total_strains`, `total_images`, `total_segments`, `indexed_points`

### 6.8 Species Distribution
1. `GET /api/v1/dashboard/species-distribution`
2. Expect array of `{species_name, image_count}`
