import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class CourseStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    HIDDEN = "hidden"
    BANNED = "banned"


class LessonContentType(enum.Enum):
    TEXT = "text"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"


class LessonModerationStatus(enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BlockContentType(enum.Enum):
    TEXT = "text"
    VIDEO = "video"
    FILE = "file"
    LINK = "link"


class BlockModerationStatus(enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MediaAssetType(enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"


class MediaAssetStatus(enum.Enum):
    PENDING = "pending"
    READY = "ready"
    REJECTED = "rejected"


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    courses = relationship("Course", back_populates="category")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        Index("ix_courses_visible_status_price", "status", "is_deleted", "price"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)

    status = Column(
        Enum(CourseStatus),
        default=CourseStatus.DRAFT,
        server_default="DRAFT",
        nullable=False,
    )
    is_deleted = Column(
        Boolean,
        default=False,
        server_default=text("false"),
        nullable=False,
    )

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="courses")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    author = relationship("User", back_populates="courses")

    lessons = relationship("Lesson", back_populates="course", cascade="all, delete-orphan")
    sections = relationship("CourseSection", back_populates="course", cascade="all, delete-orphan")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        Index("ix_lessons_course_id_position", "course_id", "position"),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    video_url = Column(String)
    content_type = Column(
        Enum(LessonContentType),
        default=LessonContentType.TEXT,
        server_default="TEXT",
        nullable=False,
    )
    content = Column(Text, nullable=True)
    attachment_url = Column(String, nullable=True)
    external_url = Column(String, nullable=True)
    moderation_status = Column(
        Enum(LessonModerationStatus),
        default=LessonModerationStatus.NOT_REQUIRED,
        server_default="NOT_REQUIRED",
        nullable=False,
    )
    position = Column(Integer, default=1, server_default="1", nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="lessons")


class CourseSection(Base):
    __tablename__ = "course_sections"
    __table_args__ = (
        Index("ix_course_sections_course_id_position", "course_id", "position"),
    )

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    position = Column(Integer, default=1, server_default="1", nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    course = relationship("Course", back_populates="sections")
    blocks = relationship("CourseBlock", back_populates="section", cascade="all, delete-orphan")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (
        Index("ix_media_assets_owner_id_created_at", "owner_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type = Column(
        Enum(MediaAssetType),
        nullable=False,
    )
    mime_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    storage_url = Column(String, nullable=False)
    status = Column(
        Enum(MediaAssetStatus),
        default=MediaAssetStatus.PENDING,
        server_default="PENDING",
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    blocks = relationship("CourseBlock", back_populates="media_asset")


class CourseBlock(Base):
    __tablename__ = "course_blocks"
    __table_args__ = (
        Index("ix_course_blocks_section_id_position", "section_id", "position"),
    )

    id = Column(Integer, primary_key=True, index=True)
    section_id = Column(Integer, ForeignKey("course_sections.id", ondelete="CASCADE"), nullable=False, index=True)
    content_type = Column(
        Enum(BlockContentType),
        nullable=False,
        default=BlockContentType.TEXT,
        server_default="TEXT",
    )
    position = Column(Integer, default=1, server_default="1", nullable=False)

    text_content = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)
    file_asset_id = Column(Integer, ForeignKey("media_assets.id", ondelete="SET NULL"), nullable=True)
    external_url = Column(String, nullable=True)
    moderation_status = Column(
        Enum(BlockModerationStatus),
        nullable=False,
        default=BlockModerationStatus.NOT_REQUIRED,
        server_default="NOT_REQUIRED",
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    section = relationship("CourseSection", back_populates="blocks")
    media_asset = relationship("MediaAsset", back_populates="blocks")
