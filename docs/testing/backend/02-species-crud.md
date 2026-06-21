# Manual Test: Species CRUD

## Preconditions
- Auth token from owner login (see 01-auth-flow.md)

## Test Steps

### 2.1 Create Species (Owner)
1. `POST /api/v1/species` with `{"name":"Penicillium commune","description":"Common mold"}`, Authorization: Bearer `<owner_token>`
2. Expect `201 Created`, response includes `id`, `name`, `description`, `created_at`, `updated_at`

### 2.2 Create Species (User - Forbidden)
1. Login as regular user
2. `POST /api/v1/species` with `{"name":"Aspergillus niger"}`
3. Expect `403 Forbidden`

### 2.3 List Species (Any Authenticated User)
1. `GET /api/v1/species`, Authorization: Bearer `<user_token>`
2. Expect `200 OK`, response has `items` array and `total` count

### 2.4 List Species with Pagination
1. `GET /api/v1/species?offset=0&limit=10`
2. Expect `items` length ≤ 10, `total` reflects all species

### 2.5 Get Single Species
1. `GET /api/v1/species/{id}` (use ID from create)
2. Expect `200 OK`, all fields present

### 2.6 Get Non-Existent Species
1. `GET /api/v1/species/00000000-0000-0000-0000-000000000000`
2. Expect `404 Not Found`, RFC 7807 format

### 2.7 Update Species (Owner)
1. `PATCH /api/v1/species/{id}` with `{"description":"Updated description"}`
2. Expect `200 OK`, `updated_at` has changed

### 2.8 Duplicate Species Name
1. `POST /api/v1/species` with existing name
2. Expect `409 Conflict`

### 2.9 Delete Species (Owner)
1. `DELETE /api/v1/species/{id}`
2. Expect `204 No Content`
3. `GET /api/v1/species/{id}` → `404 Not Found`
