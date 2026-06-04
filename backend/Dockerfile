# syntax=docker/dockerfile:1

# =============================================================================
# MycoAI Backend — Multi-stage Dockerfile
# =============================================================================
# Targets:
#   builder   → installs prod deps via uv (shared cache layer)
#   dev       → full dev deps + hot reload (default when building from compose)
#   prod      → minimal runtime, non-root user, healthcheck
#
# Build (no BuildKit required):
#   docker build -t mycoai-backend:dev --target dev backend/
#   docker build -t mycoai-backend:prod --target prod backend/
#
# With BuildKit available, append --build-arg BUILDKIT=1 for cache mounts.
# =============================================================================

# ---- Python / uv base -------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS uv-base
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app


# ---- Builder: prod dependencies only ---------------------------------------
FROM uv-base AS builder
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev


# ---- Development ------------------------------------------------------------
FROM python:3.13-slim-bookworm AS dev

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=uv-base /usr/local/bin/uv /usr/local/bin/uv
COPY --from=builder --chown=root:root /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app
COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-install-project --all-groups

COPY . .

RUN uv sync --frozen --all-groups

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "mycoai_retrieval_backend.app:app", \
     "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ---- Production -------------------------------------------------------------
FROM python:3.13-slim-bookworm AS prod

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

RUN addgroup --gid 1001 --system appgroup && \
    adduser --uid 1001 --system appuser --ingroup appgroup

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY --chown=appuser:appgroup . .

USER 1001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -sf http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "mycoai_retrieval_backend.app:app", \
     "--host", "0.0.0.0", "--port", "8000"]
