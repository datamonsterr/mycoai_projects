# Technical Spec: Database Design

## Overview

Design the relational database schema for media, species, strains, images,
users, feedback, retrieval jobs, index jobs, candidate models, and audit
logging.

---

## Database Engine

**[DECISION: Database engine]** (also in 01-tech-stack.md)

Choices:
- A) **PostgreSQL 16** — production-grade, pgvector extension available,
  JSONB support, concurrent-safe **(Recommended)**
- B) SQLite — simpler, single-file, no concurrent writes
- C) MySQL 8 — similar to PostgreSQL but fewer features

---

## Schema Design

### Users & Auth

    users
    ----
    id              UUID PK
    email           VARCHAR(255) UNIQUE NOT NULL
    password_hash   VARCHAR(255) NOT NULL
    name            VARCHAR(255) NOT NULL
    role            VARCHAR(20) NOT NULL DEFAULT 'user'  -- 'user' | 'owner'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    refresh_tokens
    --------------
    id              UUID PK
    user_id         UUID FK -> users.id
    token_hash      VARCHAR(255) UNIQUE NOT NULL
    expires_at      TIMESTAMPTZ NOT NULL
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

### Taxonomy

    media
    -----
    id              UUID PK
    name            VARCHAR(255) UNIQUE NOT NULL
    description     TEXT
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    archived_at     TIMESTAMPTZ

    species
    -------
    id              UUID PK
    name            VARCHAR(255) UNIQUE NOT NULL
    description     TEXT
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    archived_at     TIMESTAMPTZ

    strains
    -------
    id              UUID PK
    name            VARCHAR(255) NOT NULL
    source          VARCHAR(50) NOT NULL  -- 'curated_primary',
                                          -- 'incoming_low_quality',
                                          -- 'user_upload'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    UNIQUE(name)

### Images & Segments

    images
    ------
    id              UUID PK
    strain_id       UUID FK -> strains.id
    species_id      UUID FK -> species.id
    media_id        UUID FK -> media.id
    angle           VARCHAR(10)           -- ob, rev
    file_path       VARCHAR(500) NOT NULL  -- relative to storage root
    prepared_path   VARCHAR(500)          -- preprocessed image
    pipeline_path   VARCHAR(500)          -- visualization
    data_update_status VARCHAR(30) NOT NULL DEFAULT 'current'
                    -- 'current'|'updated_requires_reindex'|'archived'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    segments
    --------
    id              UUID PK
    image_id        UUID FK -> images.id
    segment_index   INTEGER NOT NULL       -- 0, 1, 2
    crop_path       VARCHAR(500) NOT NULL
    bbox_x          INTEGER NOT NULL
    bbox_y          INTEGER NOT NULL
    bbox_w          INTEGER NOT NULL
    bbox_h          INTEGER NOT NULL
    segmentation_method VARCHAR(20) NOT NULL  -- 'kmeans' | 'contour'
    qdrant_point_id UUID                   -- linked Qdrant point (nullable until
                                           -- indexed)
    is_archived     BOOLEAN NOT NULL DEFAULT FALSE
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    UNIQUE(image_id, segment_index)

### Retrieval Jobs

    retrieval_jobs
    --------------
    id              UUID PK
    user_id         UUID FK -> users.id
    job_type        VARCHAR(20) NOT NULL   -- 'single' | 'batch'
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    -- 'pending'|'processing'|'completed'|'failed'
    config          JSONB NOT NULL          -- k, aggregation, env_strategy
    input_summary   JSONB                   -- {strain_count, image_count,
                                            --  media_list}
    error_message   TEXT
    started_at      TIMESTAMPTZ
    completed_at    TIMESTAMPTZ
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    retrieval_results
    -----------------
    id              UUID PK
    job_id          UUID FK -> retrieval_jobs.id
    strain_name     VARCHAR(255) NOT NULL
    rank            INTEGER NOT NULL
    species_name    VARCHAR(255) NOT NULL
    score           FLOAT NOT NULL         -- 0.0 - 1.0

    retrieval_neighbors
    -------------------
    id              UUID PK
    result_id       UUID FK -> retrieval_results.id
    neighbor_strain VARCHAR(255) NOT NULL
    neighbor_species VARCHAR(255) NOT NULL
    similarity      FLOAT NOT NULL
    media           VARCHAR(20) NOT NULL
    segment_index   INTEGER NOT NULL

### Feedback

    feedback
    --------
    id              UUID PK
    submitter_id    UUID FK -> users.id
    reviewer_id     UUID FK -> users.id (nullable)
    source          VARCHAR(20) NOT NULL   -- 'retrieval_result'
    feedback_type   VARCHAR(30) NOT NULL   -- 'wrong_prediction'|'issue'|
                                           -- 'contribution'
    query_strain    VARCHAR(255) NOT NULL
    result_id       UUID FK -> retrieval_results.id NOT NULL
    image_id        UUID FK -> images.id (nullable)
    predicted_species VARCHAR(255)
    suggested_species VARCHAR(255)
    description     TEXT NOT NULL
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                    -- 'pending'|'accepted'|'rejected'|'deferred'
    review_note     TEXT
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    reviewed_at     TIMESTAMPTZ

### Index Jobs

    index_jobs
    ----------
    id              UUID PK
    triggered_by    UUID FK -> users.id
    job_type        VARCHAR(20) NOT NULL   -- 'qdrant_reindex'
    status          VARCHAR(20) NOT NULL DEFAULT 'pending'
    progress        JSONB                  -- {stage, current, total}
    changes_since_last JSONB               -- {items_updated, items_archived,
                                           --  feedback_accepted,
                                           --  contributions_accepted}
    model_version   VARCHAR(50)
    started_at      TIMESTAMPTZ
    completed_at    TIMESTAMPTZ
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

### Candidate Models

    candidate_models
    ----------------
    id              UUID PK
    uploaded_by     UUID FK -> users.id
    version         VARCHAR(50) NOT NULL
    status          VARCHAR(20) NOT NULL   -- 'uploaded'|'evaluating'|
                                           -- 'promoted'|'rejected'
    artifact_path   TEXT NOT NULL
    evaluation_report JSONB
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    reviewed_at     TIMESTAMPTZ

### Audit Log

    audit_log
    ---------
    id              BIGSERIAL PK
    user_id         UUID FK -> users.id
    action          VARCHAR(50) NOT NULL    -- 'create_species', 'archive_strain',
                                            -- 'accept_feedback', etc.
    entity_type     VARCHAR(50) NOT NULL    -- 'species', 'media', 'strain',
                                            -- 'image', 'feedback', 'user'
    entity_id       UUID
    changes         JSONB                   -- {field: {old, new}}
    ip_address      INET
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()

    CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
    CREATE INDEX idx_audit_log_user ON audit_log(user_id);
    CREATE INDEX idx_audit_log_created ON audit_log(created_at);

### Qdrant Index Tracking

    qdrant_index_state
    ------------------
    id              UUID PK
    segment_id      UUID FK -> segments.id
    qdrant_point_id UUID NOT NULL
    collection_name VARCHAR(100) NOT NULL
    indexed_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    last_updated    TIMESTAMPTZ NOT NULL DEFAULT NOW()
    is_active       BOOLEAN NOT NULL DEFAULT TRUE

---

## Schema Decisions

**[DECISION: UUID vs serial primary keys]**

Choices:
- A) **UUID v4** — distributed-safe, no collision risk, no sequential
  enumeration **(Recommended)**
- B) SERIAL / BIGSERIAL — smaller, faster joins, sequential
- C) ULID — time-sortable UUID alternative

**[DECISION: Soft delete strategy]**

Choices:
- A) **is_archived flag + archived_at timestamp** — simple queries,
  restore is a flag flip. Applied to species, media, and segments.
  Images use data_update_status with an `archived` state.
  **(Recommended)**
- B) Separate archive tables — clean active tables, more complex queries
- C) Move to separate schema — PostgreSQL schema-level isolation

**[DECISION: Where to store Qdrant point IDs]**

Choices:
- A) **In segments table (qdrant_point_id) and qdrant_index_state
  table** — segments holds the live FK, qdrant_index_state tracks
  collection/indexing metadata. Two-table approach gives operational
  flexibility while keeping the segments row lightweight.
  **(Recommended)**
- B) Separate qdrant_index_state table — normalized, more flexible
- C) In Qdrant payload only — no DB tracking, risk of drift

**[DECISION: JSONB vs normalized tables for job configs]**

Choices:
- A) **JSONB for config/progress — normalized for relations** — flexible
  schema for evolving job configs, strict FK for entity relations
  **(Recommended)**
- B) All normalized — rigid schema, many migrations
- C) All JSONB — flexible but no referential integrity
