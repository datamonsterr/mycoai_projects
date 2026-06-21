# Manual Test: Authentication Flow

## Preconditions
- Backend running: `docker compose up -d backend postgres redis`
- No owner user exists (fresh database)

## Test Steps

### 1.1 Owner Registration (First User)
1. `POST /api/v1/auth/register` with `{"email":"owner@test.com","password":"Test1234!","name":"Owner"}`
2. Expect `201 Created`, response contains `access_token`, `refresh_token`, `user` with `role: "owner"`
3. Verify: `/health` returns `{"status":"ok"}`

### 1.2 Owner Login
1. `POST /api/v1/auth/login` with `{"email":"owner@test.com","password":"Test1234!"}`
2. Expect `200 OK`, `access_token` and `refresh_token` present
3. Verify token format: 3-part JWT (header.payload.signature)

### 1.3 Token Refresh
1. Take `refresh_token` from login response
2. `POST /api/v1/auth/refresh` with `{"refresh_token":"<token>"}`
3. Expect `200 OK`, new `access_token` and `refresh_token`

### 1.4 Invalid Login
1. `POST /api/v1/auth/login` with wrong password
2. Expect `401 Unauthorized`, RFC 7807 problem details format

### 1.5 Expired Token
1. Use an expired/invalid JWT in Authorization header
2. `GET /api/v1/species`
3. Expect `401 Unauthorized`

### 1.6 Logout
1. `POST /api/v1/auth/logout` with valid `refresh_token`
2. Expect `204 No Content`
3. Attempt refresh with same token → `401 Unauthorized`

### 1.7 Admin Invite Flow (Owner Only)
1. Owner: `POST /api/v1/admin/invite` with `{"email":"user@test.com","role":"user"}`
2. Expect `201 Created` with `invite_token` and `invite_link`
3. New user: `POST /api/v1/auth/register-with-token` with invite token + password
4. Expect `201 Created`, role matches invitation
