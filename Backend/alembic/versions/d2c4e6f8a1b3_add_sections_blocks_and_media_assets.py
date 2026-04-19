"""Add sections, blocks and media assets

Revision ID: d2c4e6f8a1b3
Revises: b1f8c6d3e4a2
Create Date: 2026-04-19 18:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2c4e6f8a1b3"
down_revision: Union[str, Sequence[str], None] = "b1f8c6d3e4a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


block_content_type_enum = sa.Enum(
    "TEXT",
    "VIDEO",
    "FILE",
    "LINK",
    name="blockcontenttype",
    create_type=False,
)
block_moderation_status_enum = sa.Enum(
    "NOT_REQUIRED",
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="blockmoderationstatus",
    create_type=False,
)
media_asset_type_enum = sa.Enum(
    "IMAGE",
    "VIDEO",
    "FILE",
    name="mediaassettype",
    create_type=False,
)
media_asset_status_enum = sa.Enum(
    "PENDING",
    "READY",
    "REJECTED",
    name="mediaassetstatus",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "course_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_course_sections_id"), "course_sections", ["id"], unique=False)
    op.create_index(
        "ix_course_sections_course_id_position",
        "course_sections",
        ["course_id", "position"],
        unique=False,
    )

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", media_asset_type_enum, nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_url", sa.String(), nullable=False),
        sa.Column("status", media_asset_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_media_assets_id"), "media_assets", ["id"], unique=False)
    op.create_index(op.f("ix_media_assets_owner_id"), "media_assets", ["owner_id"], unique=False)
    op.create_index(
        "ix_media_assets_owner_id_created_at",
        "media_assets",
        ["owner_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "course_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("content_type", block_content_type_enum, nullable=False, server_default="TEXT"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("text_content", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(), nullable=True),
        sa.Column("file_asset_id", sa.Integer(), nullable=True),
        sa.Column("external_url", sa.String(), nullable=True),
        sa.Column(
            "moderation_status",
            block_moderation_status_enum,
            nullable=False,
            server_default="NOT_REQUIRED",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["file_asset_id"], ["media_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["section_id"], ["course_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_course_blocks_id"), "course_blocks", ["id"], unique=False)
    op.create_index(op.f("ix_course_blocks_section_id"), "course_blocks", ["section_id"], unique=False)
    op.create_index(
        "ix_course_blocks_section_id_position",
        "course_blocks",
        ["section_id", "position"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_course_blocks_section_id_position", table_name="course_blocks")
    op.drop_index(op.f("ix_course_blocks_section_id"), table_name="course_blocks")
    op.drop_index(op.f("ix_course_blocks_id"), table_name="course_blocks")
    op.drop_table("course_blocks")

    op.drop_index("ix_media_assets_owner_id_created_at", table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_owner_id"), table_name="media_assets")
    op.drop_index(op.f("ix_media_assets_id"), table_name="media_assets")
    op.drop_table("media_assets")

    op.drop_index("ix_course_sections_course_id_position", table_name="course_sections")
    op.drop_index(op.f("ix_course_sections_id"), table_name="course_sections")
    op.drop_table("course_sections")

    op.execute("DROP TYPE IF EXISTS mediaassetstatus")
    op.execute("DROP TYPE IF EXISTS mediaassettype")
    op.execute("DROP TYPE IF EXISTS blockmoderationstatus")
    op.execute("DROP TYPE IF EXISTS blockcontenttype")
