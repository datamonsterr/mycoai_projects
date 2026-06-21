# Manual Test: Image Upload & Segmentation

## Preconditions
- Auth token from owner login
- At least one species and one media exist
- A test image (PNG/JPEG) available at `/tmp/test_fungi.png`

### 4.1 Upload Single Image
1. `POST /api/v1/images` with multipart form:
   - `image`: file upload (test_fungi.png)
   - `strain`: "DTO-148-C8"
   - `media`: "CYA"
   - `species`: species name or ID
   - `method`: "kmeans"
2. Expect `200 OK`, response includes `image_id`, `segments` array, `source_url`, `segmentation_method`

### 4.2 Verify Segment Artifacts
1. Check `Dataset/uploads/{strain}/{media}/{image_id}/` directory
2. Expect: `source.jpg`, `prepared.jpg`, `bbox_kmeans.jpg`, `pipeline_kmeans.jpg`, `segments/segment_0.jpg`

### 4.3 Upload with Contour Method
1. Same as 4.1 but `method`: "contour"
2. Expect 200, `segmentation_method`: "contour"

### 4.4 List Images
1. `GET /api/v1/images`
2. Expect `200 OK`, paginated with `items` and `total`

### 4.5 Get Image Detail
1. `GET /api/v1/images/{image_id}`
2. Expect segment list, strain info, species info, media info

### 4.6 Update Segments (Patch)
1. `PATCH /api/v1/images/{image_id}/segments` with modified segment bboxes
2. Expect `200 OK`, segments updated

### 4.7 Batch Import (ZIP)
1. Create ZIP with images following DTO naming convention
2. `POST /api/v1/images/batch` with multipart ZIP file
3. Expect `200 OK`, results array with per-image status

### 4.8 Delete Image
1. `DELETE /api/v1/images/{image_id}`
2. Expect `204 No Content`
3. Verify upload directory cleaned up
