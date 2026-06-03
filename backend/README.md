# MycoAI Retrieval Backend

FastAPI backend for retrieval, indexing, and scientist-facing data management
workflows around `fungal-cv-qdrant`, especially outputs from the
`retrieval` and `kmeans_segmentation` experiment pipelines.

## Stack

- Python 3.13
- FastAPI
- Uvicorn
- Ruff
- MyPy
- Pytest
- uv

## Commands

```bash
uv sync --all-groups
uv run mycoai-retrieval-backend
uv run ruff check .
uv run ruff format .
uv run mypy src
uv run pytest
```

## API

- `GET /health` - healthcheck endpoint
- `GET /` - service metadata

## Product Boundary

- Backend features may inspect `../fungal-cv-qdrant/src/experiments/` to
  understand validated experiment behavior.
- Backend code and tests MUST reimplement product behavior locally and MUST NOT
  import runtime code directly from `fungal-cv-qdrant/`.
- Changes derived from experiment outputs should document the source command,
  artifact, and consumer API surface in the accompanying spec or PR.
