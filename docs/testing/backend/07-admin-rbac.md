# Manual Test: Admin & RBAC

## Preconditions
- Owner user authenticated
- At least one regular user exists

### 7.1 List Users (Owner)
1. `GET /api/v1/admin/users`
2. Expect `200 OK`, list of all users with roles

### 7.2 Update User Role (Owner)
1. `PATCH /api/v1/admin/users/{user_id}/role` with `{"role":"dataowner"}`
2. Expect `200 OK`, role updated
3. Verify user now has dataowner permissions

### 7.3 Deactivate User (Owner)
1. `PATCH /api/v1/admin/users/{user_id}/status` with `{"is_active":false}`
2. Expect `200 OK`
3. Deactivated user login → `401 Unauthorized` or `403 Forbidden`

### 7.4 Reactivate User
1. `PATCH /api/v1/admin/users/{user_id}/status` with `{"is_active":true}`
2. User can login again

### 7.5 Owner-Only Endpoints (User Forbidden)
Test each with regular user token, expect `403`:
1. `POST /api/v1/species` (create)
2. `PATCH /api/v1/species/{id}` (update)
3. `DELETE /api/v1/species/{id}` (delete)
4. `POST /api/v1/media` (create)
5. `POST /api/v1/media/{id}/archive`
6. `PATCH /api/v1/admin/users/{id}/role`
7. `POST /api/v1/admin/invite`

### 7.6 Dataowner Permissions
1. Login as dataowner
2. `POST /api/v1/species` → `403 Forbidden` (dataowner cannot create species)
3. `POST /api/v1/images` → `200 OK` (can upload)
4. `GET /api/v1/images` → `200 OK` (can list)

### 7.7 Unauthenticated Access
Test without Authorization header, expect `401`:
1. `GET /api/v1/species`
2. `GET /api/v1/media`
3. `GET /api/v1/images`

### 7.8 Audit Log
1. `GET /api/v1/admin/audit-logs`
2. Expect `200 OK`, logs with `user_id`, `action`, `resource`, `timestamp`
