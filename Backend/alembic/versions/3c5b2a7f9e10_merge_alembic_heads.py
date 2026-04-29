"""merge alembic heads for auth and course branches

Revision ID: 3c5b2a7f9e10
Revises: d2c4e6f8a1b3, e1a9d4c7b2f3
Create Date: 2026-04-28 20:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3c5b2a7f9e10"
down_revision: Union[str, Sequence[str], None] = ("d2c4e6f8a1b3", "e1a9d4c7b2f3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

