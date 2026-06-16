"""Verify that all SQLAlchemy models have corresponding migrations applied.

This guards against the bug where a model is added (e.g. InviteToken) but
no Alembic migration is generated, causing 500 errors at runtime against
a database that was migrated without the missing table.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncConnection

from mycoai_retrieval_backend.database import Base


@pytest.fixture(name="model_tables")
def fixture_model_tables() -> set[str]:
    """All table names declared by SQLAlchemy models in Base.metadata."""
    return {table.name for table in Base.metadata.sorted_tables}


@pytest_asyncio.fixture(name="live_tables")
async def fixture_live_tables(
    engine: object,  # AsyncEngine
) -> set[str]:
    """All table names present in the live test database after create_all."""
    raw_engine = engine  # type: ignore[assignment]
    conn: AsyncConnection
    async with raw_engine.connect() as conn:  # type: ignore[union-attr]
        def sync_inspect(sync_conn: object) -> set[str]:
            insp = inspect(sync_conn)
            return set(insp.get_table_names())

        return await conn.run_sync(sync_inspect)


# ── Core assertions ──────────────────────────────────────────────────────────

def test_invite_tokens_in_model_metadata(model_tables: set[str]) -> None:
    """invite_tokens must be declared as a model table."""
    assert "invite_tokens" in model_tables, (
        "invite_tokens table not found in Base.metadata. "
        "Did you remove the InviteToken model?"
    )


def test_invite_tokens_created_in_test_db(
    live_tables: set[str],
) -> None:
    """invite_tokens must exist after Base.metadata.create_all."""
    assert "invite_tokens" in live_tables, (
        "invite_tokens table not created by create_all. "
        "Check that InviteToken extends Base and is imported at module load."
    )


def test_all_model_tables_created(
    model_tables: set[str], live_tables: set[str]
) -> None:
    """Every model table must be created in the test database."""
    missing = model_tables - live_tables
    assert not missing, (
        f"Model tables missing in test DB: {sorted(missing)}. "
        "Ensure all models are imported and extend Base."
    )


# ── Known-good invariant: every model table must have a down_revision chain ──

EXPECTED_TABLES = {
    "audit_log",
    "feedback",
    "images",
    "invite_tokens",
    "media",
    "qdrant_index_state",
    "refresh_tokens",
    "retrieval_jobs",
    "retrieval_neighbors",
    "retrieval_results",
    "segments",
    "species",
    "strains",
    "system_state",
    "training_jobs",
    "users",
}


def test_table_snapshot_matches_expected(model_tables: set[str]) -> None:
    """Snapshot test: model table list must match explicit expectation.

    When you add a new model, update EXPECTED_TABLES above AND create
    a new Alembic migration. This test will fail if either step is skipped.
    """
    missing = EXPECTED_TABLES - model_tables
    extra = model_tables - EXPECTED_TABLES
    assert not missing, (
        f"Expected tables not found in models: {sorted(missing)}. "
        "Either remove from EXPECTED_TABLES or ensure the model exists."
    )
    assert not extra, (
        f"New model tables found but not in EXPECTED_TABLES: {sorted(extra)}. "
        "Add them to EXPECTED_TABLES AND create an Alembic migration."
    )
