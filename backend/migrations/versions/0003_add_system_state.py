"""Add system_state table for global key-value state (retraining counter)."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_system_state"
down_revision: str | None = "0002_add_media_fks_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "system_state",
        sa.Column("key", sa.String(length=100), primary_key=True),
        sa.Column(
            "value",
            postgresql.JSONB(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Seed initial retraining counter
    op.execute(
        """
        INSERT INTO system_state (key, value, updated_at)
        VALUES (
            'retraining_counter',
            '{"images_added": 0, "bbox_corrections": 0, "items_archived": 0, "species_added": 0, "last_reset_at": null, "threshold": 20}'::jsonb,
            now()
        )
        """
    )


def downgrade() -> None:
    op.drop_table("system_state")
