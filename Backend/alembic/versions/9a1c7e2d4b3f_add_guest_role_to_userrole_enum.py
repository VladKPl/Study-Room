"""Add guest role to userrole enum

Revision ID: 9a1c7e2d4b3f
Revises: 7b9e1f4c2a10
Create Date: 2026-02-26 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "9a1c7e2d4b3f"
down_revision: Union[str, Sequence[str], None] = "7b9e1f4c2a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'guest'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be dropped safely in a simple downgrade.
    pass
