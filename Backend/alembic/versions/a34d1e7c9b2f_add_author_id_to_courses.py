"""Add author_id to courses

Revision ID: a34d1e7c9b2f
Revises: 9a1c7e2d4b3f
Create Date: 2026-02-27 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a34d1e7c9b2f"
down_revision: Union[str, Sequence[str], None] = "9a1c7e2d4b3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("author_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_courses_author_id"), "courses", ["author_id"], unique=False)
    op.create_foreign_key(
        "fk_courses_author_id_users",
        "courses",
        "users",
        ["author_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_courses_author_id_users", "courses", type_="foreignkey")
    op.drop_index(op.f("ix_courses_author_id"), table_name="courses")
    op.drop_column("courses", "author_id")
