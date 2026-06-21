# Manual Test: Media CRUD

## Preconditions
- Auth token from owner login (see 01-auth-flow.md)

## Test Steps

### 3.1 Create Media
1. `POST /api/v1/media` with `{"name":"CYA","description":"Czapek Yeast Autolysate agar"}`
2. Expect `201 Created`, response includes `id`, `name`, `description`, `is_archived: false`

### 3.2 List Media
1. `GET /api/v1/media`
2. Expect `200 OK`, `items` contains created media, `total` ≥ 1

### 3.3 Get Media by ID
1. `GET /api/v1/media/{id}`
2. Expect `200 OK`, all fields present

### 3.4 Update Media
1. `PATCH /api/v1/media/{id}` with `{"description":"Updated agar description"}`
2. Expect `200 OK`

### 3.5 Archive Media
1. `POST /api/v1/media/{id}/archive`
2. Expect `200 OK`, `is_archived: true`
3. `GET /api/v1/media` → archived media not in list (unless `include_archived=true`)

### 3.6 Restore Media
1. `POST /api/v1/media/{id}/restore`
2. Expect `200 OK`, `is_archived: false`

### 3.7 Duplicate Media Name
1. `POST /api/v1/media` with same name as existing
2. Expect `409 Conflict`
