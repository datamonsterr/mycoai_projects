"""Add missing columns: archived_at on images.

neighbor_image_id on retrieval_neighbors.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_add_missing_columns"
down_revision: str | None = "0004_add_invite_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("images") as batch:
        try:
            batch.add_column(
                sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
            )
        except Exception:
            pass

    with op.batch_alter_table("retrieval_neighbors") as batch:
        try:
            batch.add_column(
                sa.Column("neighbor_image_id", sa.String(length=255), nullable=True)
            )
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table("retrieval_neighbors") as batch:
        try:
            batch.drop_column("neighbor_image_id")
        except Exception:
            pass

    with op.batch_alter_table("images") as batch:
        try:
            batch.drop_column("archived_at")
        except Exception:
            pass
