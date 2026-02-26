"""Add defaults and visibility index for courses

Revision ID: 5f2d9c1b8e4a
Revises: 2457485d5437
Create Date: 2026-02-26 18:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5f2d9c1b8e4a"
down_revision: Union[str, Sequence[str], None] = "2457485d5437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "courses",
        "status",
        existing_type=sa.Enum("DRAFT", "PUBLISHED", "HIDDEN", "BANNED", name="coursestatus"),
        server_default=sa.text("'DRAFT'"),
        existing_nullable=False,
    )
    op.alter_column(
        "courses",
        "is_deleted",
        existing_type=sa.Boolean(),
        server_default=sa.text("false"),
        existing_nullable=False,
    )
    op.create_index(
        "ix_courses_visible_status_price",
        "courses",
        ["status", "is_deleted", "price"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_courses_visible_status_price", table_name="courses")
    op.alter_column(
        "courses",
        "is_deleted",
        existing_type=sa.Boolean(),
        server_default=None,
        existing_nullable=False,
    )
    op.alter_column(
        "courses",
        "status",
        existing_type=sa.Enum("DRAFT", "PUBLISHED", "HIDDEN", "BANNED", name="coursestatus"),
        server_default=None,
        existing_nullable=False,
    )
