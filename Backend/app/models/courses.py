import enum

from sqlalchemy import Boolean, Column, Enum, Float, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import relationship

from app.database import Base

class CourseStatus(enum.Enum):
    DRAFT = "draft"          # Черновик (видит только автор)
    PUBLISHED = "published"  # Опубликован (видят все)
    HIDDEN = "hidden"        # Скрыт автором (не отображается в поиске)
    BANNED = "banned"        # Заблокирован модератором

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

class Lesson(Base):
    __tablename__ = "lessons"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    video_url = Column(String) # Ссылка на видео
    course_id = Column(Integer, ForeignKey("courses.id"))

    course = relationship("Course", back_populates="lessons")
