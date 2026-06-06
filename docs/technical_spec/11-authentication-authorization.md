# Technical Spec: Authentication & Authorization

## Overview

Design the authentication system: registration, login, JWT management,
role-based access control, and security considerations.

---

## Authentication Flow

    Registration:
    POST /api/v1/auth/register
    Body: { email, password, name }
    -> Create user with role="user"
    -> Return access_token + refresh_token

    Initial Data Owner provisioning:
    python -m mycoai_retrieval_backend.create-owner --email owner@example.com
    -> Assign initial role="owner" by internal script

    Login:
    POST /api/v1/auth/login
    Body: { email, password }
    -> Verify credentials
    -> Return access_token + refresh_token

    Token refresh:
    POST /api/v1/auth/refresh
    Body: { refresh_token }
    -> Verify refresh token
    -> Return new access_token

    Logout:
    POST /api/v1/auth/logout
    Header: Authorization: Bearer <access_token>
    -> Revoke refresh_token in DB

---

## Token Design

**[DECISION: Token configuration]**

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| Access token lifetime | 1 hour | Short-lived, refresh often |
| Refresh token lifetime | 30 days | Long-lived, revokable |
| Algorithm | HS256 | Symmetric, single-service |
| Token type | Bearer | Standard |

**[DECISION: Token storage on client]**

Choices:
- A) **httpOnly cookie for refresh token + memory for access token** —
  most secure, XSS-resistant. Access token in JS memory (lost on
  refresh, auto-refreshed). **(Recommended)**
- B) localStorage for both — simpler, XSS-vulnerable
- C) httpOnly cookies for both — CSRF concerns, need CSRF token

**Implementation plan:**

    Access token: stored in JS memory (not localStorage)
    Refresh token: stored in httpOnly, Secure, SameSite=Strict cookie
    On page load: attempt refresh, put access token in memory
    On 401: attempt refresh, if fails -> redirect to login

---

## Password Policy

**[DECISION: Password requirements]**

Choices:
- A) **Minimum 8 chars, any characters** — reasonable baseline
  **(Recommended)**
- B) Minimum 12 chars, at least one uppercase + number + special
- C) No policy (accept anything)

**Hashing:** bcrypt via passlib, 12 rounds

---

## Authorization: Role-Based Access Control

### Roles

| Role | Description |
|------|-------------|
| `user` | User — can upload, retrieve Species, download batch results, submit feedback/contribution proposals from retrieval results |
| `owner` | Data Owner — User access plus reference-data indexing, metadata/dataset/user governance, Qdrant re-indexing, Candidate Model assessment |

The Data Owner role inherits all User permissions. Any endpoint marked
`User` is also accessible to Data Owners.

### Implementation

    from fastapi import Depends, HTTPException, status

    async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        payload = decode_jwt(token)
        user = await user_repo.get_by_id(db, payload["sub"])
        if not user or not user.is_active:
            raise HTTPException(status_code=401)
        return user

    def require_role(required_role: str):
        async def role_checker(user: User = Depends(get_current_user)):
            if user.role != required_role:
                raise HTTPException(status_code=403)
            return user
        return role_checker

    # Usage in routes:
    @router.post("/species")
    async def create_species(
        data: SpeciesCreate,
        user: User = Depends(require_role("owner")),
        db: AsyncSession = Depends(get_db)
    ):
        ...

### Permission Matrix

| Endpoint group | user | owner |
|---------------|------|-------|
| Auth (register, login, refresh, logout) | Yes | Yes |
| Images (upload, query status) | Yes | Yes |
| Retrieval (query, results) | Yes | Yes |
| Species/Media metadata (read for retrieval forms) | Yes | Yes |
| Species metadata (create, update, archive) | No | Yes |
| Media metadata (create, update, archive) | No | Yes |
| Reference dataset browse/search/filter/group | No | Yes |
| Reference dataset update/archive/restore | No | Yes |
| Feedback (submit from retrieval results, view own) | Yes | Yes |
| Feedback (inbox, review) | No | Yes |
| Qdrant re-index | No | Yes |
| Candidate Model upload/assessment/promotion | No | Yes |
| Dashboard (stats) | No | Yes |
| Admin (users, audit log) | No | Yes |

---

## First User Setup

**[DECISION: How first data owner is created]**

Decision:
- Initial Data Owner is created by seed script:
  `python -m mycoai_retrieval_backend.create-owner --email admin@example.com`
- Self-registration remains available for Users.
- Data Owners can promote Users after bootstrap.
- Data Owners can invite Users by onboarding email for convenience.

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Brute force login | Rate limit: 5 attempts per IP per minute |
| Token theft | Short-lived access tokens, httpOnly refresh tokens |
| CSRF | SameSite=Strict on cookies, token in Authorization header |
| SQL injection | SQLAlchemy parameterized queries |
| File upload | Validate MIME type, limit size (50MB), scan for malware |
| Password storage | bcrypt hash, never log passwords |
| CORS | Restrict to known frontend origins |

---

## Session Management

**[DECISION: Multi-session support]**

Choices:
- A) **Multiple refresh tokens per user** — user can be logged in on
  multiple devices. Each refresh token tracked in DB.
  **(Recommended)**
- B) Single session — logging in on new device invalidates old
- C) Stateless (no refresh token tracking) — simpler, can't revoke

---

## Rate Limiting

**[DECISION: Rate limiting library]**

Choices:
- A) **slowapi** — FastAPI-compatible, Redis-backed, decorator-based
  **(Recommended)**
- B) Custom middleware — more control, more work
- C) None — handle at proxy/load balancer level
