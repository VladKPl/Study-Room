"""Add lesson editor fields

Revision ID: b1f8c6d3e4a2
Revises: 6d8f4c1b2e90
Create Date: 2026-04-19 17:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b1f8c6d3e4a2"
down_revision: Union[str, Sequence[str], None] = "6d8f4c1b2e90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


lesson_content_type_enum = sa.Enum(
    "TEXT",
    "VIDEO",
    "FILE",
    "LINK",
    name="lessoncontenttype",
)
lesson_moderation_status_enum = sa.Enum(
    "NOT_REQUIRED",
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="lessonmoderationstatus",
)


def upgrade() -> None:
    bind = op.get_bind()
    lesson_content_type_enum.create(bind, checkfirst=True)
    lesson_moderation_status_enum.create(bind, checkfirst=True)

    op.add_column(
        "lessons",
        sa.Column(
            "content_type",
            lesson_content_type_enum,
            nullable=False,
            server_default="TEXT",
        ),
    )
    op.add_column("lessons", sa.Column("content", sa.Text(), nullable=True))
    op.add_column("lessons", sa.Column("attachment_url", sa.String(), nullable=True))
    op.add_column("lessons", sa.Column("external_url", sa.String(), nullable=True))
    op.add_column(
        "lessons",
        sa.Column(
            "moderation_status",
            lesson_moderation_status_enum,
            nullable=False,
            server_default="NOT_REQUIRED",
        ),
    )
    op.add_column(
        "lessons",
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_lessons_course_id_position",
        "lessons",
        ["course_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_lessons_course_id_position", table_name="lessons")
    op.drop_column("lessons", "position")
    op.drop_column("lessons", "moderation_status")
    op.drop_column("lessons", "external_url")
    op.drop_column("lessons", "attachment_url")
    op.drop_column("lessons", "content")
    op.drop_column("lessons", "content_type")

    bind = op.get_bind()
    lesson_moderation_status_enum.drop(bind, checkfirst=True)
    lesson_content_type_enum.drop(bind, checkfirst=True)
