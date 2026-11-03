"""Add satellite image inventory table.

Revision ID: 002_satellite_images
Revises: 001_initial_locations_risk
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_satellite_images"
down_revision: Union[str, None] = "001_initial_locations_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "satellite_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("image_filename", sa.String(length=512), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("product_type", sa.String(length=80), nullable=False),
        sa.Column("filename_date_token", sa.String(length=7), nullable=True),
        sa.Column(
            "already_in_manifest",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("hab_label", sa.String(length=50), nullable=True),
        sa.Column("label_status", sa.String(length=80), nullable=True),
        sa.Column("validation_status", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "image_path",
            name="uq_satellite_images_image_path",
        ),
    )
    op.create_index(
        "ix_satellite_images_sha256",
        "satellite_images",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_satellite_images_sha256",
        table_name="satellite_images",
    )
    op.drop_table("satellite_images")
