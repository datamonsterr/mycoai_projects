"""Add media table, image FKs, feedback_type, data_update_status."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_add_media_image_fks_feedback"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    with op.batch_alter_table("images") as batch:
        batch.add_column(
            sa.Column("species_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch.add_column(
            sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=True)
        )
        batch.add_column(
            sa.Column(
                "data_update_status",
                sa.String(length=30),
                nullable=False,
                server_default="current",
            )
        )
        batch.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch.create_foreign_key(
            "fk_images_species_id", "species", ["species_id"], ["id"]
        )
        batch.create_foreign_key("fk_images_media_id", "media", ["media_id"], ["id"])
        batch.drop_column("media")

    with op.batch_alter_table("feedback") as batch:
        batch.add_column(
            sa.Column(
                "feedback_type",
                sa.String(length=30),
                nullable=False,
                server_default="wrong_prediction",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("feedback") as batch:
        batch.drop_column("feedback_type")

    with op.batch_alter_table("images") as batch:
        batch.add_column(
            sa.Column(
                "media", sa.String(length=20), nullable=False, server_default="MEA"
            )
        )
        batch.drop_constraint("fk_images_media_id", type_="foreignkey")
        batch.drop_constraint("fk_images_species_id", type_="foreignkey")
        batch.drop_column("media_id")
        batch.drop_column("species_id")
        batch.drop_column("data_update_status")
        batch.drop_column("updated_at")

    op.drop_table("media")
