# Technical Spec: API Design

## Overview

Define the REST API contract: endpoints, request/response formats,
authentication, pagination, and error handling conventions.

---

## API Conventions

**[DECISION: URL prefix and versioning]** (also in 02-backend-architecture)

Choices:
- A) `/api/v1/` prefix — explicit versioning **(Recommended)**
- B) `/api/` only — no versioning for MVP
- C) Header-based versioning

**[DECISION: Naming convention]**

Choices:
- A) **Plural nouns, kebab-case**: `/api/v1/retrieval-jobs/`,
  `/api/v1/images/` **(Recommended)**
- B) Singular nouns: `/api/v1/image/`
- C) snake_case: `/api/v1/retrieval_jobs/`

**[DECISION: HTTP method usage]**

Convention:
- `GET` — read (list + detail)
- `POST` — create
- `PATCH` — partial update
- `DELETE` — archive (soft delete)
- Never use query params for mutations

---

## Endpoint Catalog

### Auth

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/auth/register` | None | Create account |
| POST | `/api/v1/auth/login` | None | Login, get tokens |
| POST | `/api/v1/auth/refresh` | Refresh token | Get new access token |
| POST | `/api/v1/auth/logout` | Access token | Revoke refresh token |
| GET | `/api/v1/auth/me` | Access token | Current user profile |

### Images

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/images` | User | List images (filterable) |
| POST | `/api/v1/images` | User | Upload single image |
| POST | `/api/v1/images/upload` | User | Upload single image (alias) |
| POST | `/api/v1/images/batch` | Owner | Import batch from server folder |
| POST | `/api/v1/images/batch-upload` | Owner | Upload folder (multipart files + metadata JSON) |
| GET | `/api/v1/images/{id}` | User | Image detail + segments |
| PATCH | `/api/v1/images/{id}/segments` | Owner | Update segment bounding boxes |
| GET | `/api/v1/images/{id}/segments/{idx}/crop` | User | Segment crop image |
| GET | `/api/v1/images/{id}/pipeline` | User | Pipeline visualization image |
| DELETE | `/api/v1/images/{id}` | Owner | Soft-delete image |

### Retrieval

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/retrieval/query` | User | Start retrieval job |
| GET | `/api/v1/retrieval/jobs/{id}` | User | Job status |
| GET | `/api/v1/retrieval/jobs/{id}/results` | User | Results when complete |
| POST | `/api/v1/retrieval/query-sync` | User | Synchronous query (small jobs) |

### Species

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/species` | User | List species (filtered) |
| POST | `/api/v1/species` | Owner | Create species |
| GET | `/api/v1/species/{id}` | User | Species detail + count |
| PATCH | `/api/v1/species/{id}` | Owner | Update species (rename) |
| DELETE | `/api/v1/species/{id}` | Owner | Archive species |

### Media

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/media` | User | List media (filtered) |
| POST | `/api/v1/media` | Owner | Create media |
| GET | `/api/v1/media/{id}` | User | Media detail + count |
| PATCH | `/api/v1/media/{id}` | Owner | Update media |
| DELETE | `/api/v1/media/{id}` | Owner | Archive media |

### Strains

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/strains` | User | List strains (filtered) |
| POST | `/api/v1/strains` | Owner | Create strain with images |
| GET | `/api/v1/strains/{id}` | User | Strain detail + images |
| DELETE | `/api/v1/strains/{id}` | Owner | Archive strain |

### Feedback

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/feedback` | User | Submit feedback |
| GET | `/api/v1/feedback` | User | My submitted feedback |
| GET | `/api/v1/feedback/inbox` | Owner | Pending feedback to review |
| PATCH | `/api/v1/feedback/{id}` | Owner | Accept/reject/defer |
| POST | `/api/v1/feedback/batch` | Owner | Bulk accept/reject |

### Training

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/training/status` | User | Current model info |
| GET | `/api/v1/training/jobs` | Owner | Training history |
| POST | `/api/v1/training/trigger` | Owner | Start retraining |
| GET | `/api/v1/training/jobs/{id}` | Owner | Job progress |
| POST | `/api/v1/training/jobs/{id}/cancel` | Owner | Cancel job |
| POST | `/api/v1/training/jobs/{id}/deploy` | Owner | Deploy trained model |
| POST | `/api/v1/training/rollback` | Owner | Rollback to previous model |

### Dashboard

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/dashboard/stats` | User | Counts (species, strains, images) |
| GET | `/api/v1/dashboard/charts/species` | User | Species distribution data |
| GET | `/api/v1/dashboard/charts/media` | User | Media distribution data |
| GET | `/api/v1/dashboard/charts/timeline` | User | Images over time data |
| GET | `/api/v1/dashboard/qdrant-status` | User | Index status (learned vs not) |

### Admin

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/admin/users` | Owner | List users |
| PATCH | `/api/v1/admin/users/{id}/role` | Owner | Change user role |
| GET | `/api/v1/admin/audit-log` | Owner | Audit trail |

### Index

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/index/reindex` | Owner | Trigger Qdrant re-index |
| GET | `/api/v1/index/status` | Owner | Index job status |

### Candidate Models

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1/models/candidates` | Owner | Upload candidate model |
| POST | `/api/v1/models/candidates/{id}/evaluate` | Owner | Run evaluation |
| POST | `/api/v1/models/candidates/{id}/promote` | Owner | Promote to production |
| POST | `/api/v1/models/candidates/{id}/reject` | Owner | Reject candidate |

---

## Request/Response Examples

### POST /api/v1/images/upload

Request (multipart/form-data):

    image: <binary>
    strain: "DTO 148-D1"
    media: "MEA"
    species: "Penicillium commune"
    method: "kmeans"

Response (201):

    {
      "image_id": "uuid",
      "source_url": "/static/DTO 148-D1/MEA/uuid/source.jpg",
      "segments": [...],
      "segmentation_method": "kmeans"
    }

### POST /api/v1/images/batch-upload

Upload a folder of images with optional metadata JSON.

Request (multipart/form-data):

    files: [<image1.jpg>, <image2.png>, ...]   # multiple file fields
    metadata: '{"batch_name": "mycoai_new_species", "strains": {...}}'  (optional)
    default_media: "MEA"              (default: "MEA")
    default_species: "unknown-species" (default: "unknown-species")
    method: "kmeans"                  (default: "kmeans")

Folder path in filenames is used to infer strain:
`mycoai_new_species/DTO_148-D1/image_01.jpg` → strain=DTO_148-D1

Response (202):

    {
      "status": "completed",
      "batch_name": "mycoai_new_species",
      "total": 3,
      "successful": 3,
      "failed": 0,
      "results": [
        {
          "image_id": "uuid",
          "strain": "DTO_148-D1",
          "media": "MEA",
          "species": "Penicillium commune",
          "segments": 2,
          "filename": "mycoai_new_species/DTO_148-D1/image_01.jpg"
        }
      ],
      "errors": []
    }

### POST /api/v1/retrieval/query

Request:

    {
      "image_id": "uuid",
      "k": 5,
      "aggregation": "weighted",
      "environment_strategy": "E1"
    }

Response (202):

    {
      "job_id": "uuid",
      "status": "processing",
      "estimated_seconds": 5
    }

### GET /api/v1/retrieval/jobs/{id}/results

Response (200):

    {
      "job_id": "uuid",
      "status": "completed",
      "strain": "DTO 148-D1",
      "rankings": [
        {
          "rank": 1,
          "species": "Penicillium commune",
          "score": 0.87,
          "neighbors": [
            {
              "strain": "DTO 148-D2",
              "species": "Penicillium commune",
              "similarity": 0.92,
              "media": "MEA",
              "image_thumbnail_url": "/api/v1/images/xxx/thumbnail"
            }
          ]
        }
      ]
    }

### PATCH /api/v1/admin/users/{id}/role

Request:

    {
      "role": "owner"
    }

Response (200):

    {
      "user_id": "uuid",
      "email": "user@example.com",
      "role": "owner",
      "updated_at": "2026-06-05T12:00:00Z"
    }

---

## Pagination

**[DECISION: Pagination style]**

Choices:
- A) **Offset-based**: `?offset=0&limit=50` — simplest, good for
  moderate datasets **(Recommended)**
- B) Cursor-based: `?cursor=xxx&limit=50` — stable under insertions,
  more complex
- C) Page-based: `?page=1&per_page=50` — familiar, offset under the hood

**Response format:**

    {
      "items": [...],
      "total": 143,
      "offset": 0,
      "limit": 50
    }

---

## Filtering & Sorting

Standard query parameter conventions:

    GET /api/v1/strains?species_id=xxx&media=MEA&is_archived=false
                        &search=DTO&sort_by=name&sort_order=asc
                        &offset=0&limit=50

---

## Authentication Flow

    Register:
    POST /api/v1/auth/register
    Body: { email, password, name }
    -> { access_token, refresh_token, token_type: "bearer", expires_in: 3600 }

    Login:
    POST /api/v1/auth/login
    Body: { email, password }
    -> { access_token, refresh_token, token_type: "bearer", expires_in: 3600 }

    Subsequent requests:
    Authorization: Bearer <access_token>

    On 401 (expired access token):
    POST /api/v1/auth/refresh
    Body: { refresh_token }
    -> { access_token, expires_in: 3600 }

    On refresh failure (expired refresh token):
    Client must re-authenticate via login.

    Logout:
    POST /api/v1/auth/logout
    Header: Authorization: Bearer <access_token>
    -> Revokes refresh token, access token invalidated
    -> 204 No Content

---

## Error Response Format

All errors follow RFC 7807 Problem Details:

    400 Bad Request:
    {
      "type": "https://api.mycoai.dev/errors/validation",
      "title": "Validation Error",
      "status": 400,
      "detail": "strain field is required",
      "instance": "/api/v1/images/upload",
      "errors": [
        {
          "field": "strain",
          "message": "This field is required"
        }
      ]
    }

    404 Not Found:
    {
      "type": "https://api.mycoai.dev/errors/not-found",
      "title": "Resource Not Found",
      "status": 404,
      "detail": "Image with id xxx not found",
      "instance": "/api/v1/images/xxx"
    }
