from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.courses import CourseStatus, LessonContentType, LessonModerationStatus


class LessonBase(BaseModel):
    id: int
    title: str
    content_type: LessonContentType
    content: Optional[str] = None
    video_url: Optional[str] = None
    attachment_url: Optional[str] = None
    external_url: Optional[str] = None
    moderation_status: LessonModerationStatus
    position: int
    model_config = ConfigDict(from_attributes=True)


class LessonCreate(BaseModel):
    title: str
    content_type: LessonContentType = LessonContentType.TEXT
    content: Optional[str] = None
    video_url: Optional[str] = None
    attachment_url: Optional[str] = None
    external_url: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=1)


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content_type: Optional[LessonContentType] = None
    content: Optional[str] = None
    video_url: Optional[str] = None
    attachment_url: Optional[str] = None
    external_url: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=1)


class LessonModerationUpdate(BaseModel):
    moderation_status: LessonModerationStatus


class CategoryBase(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class CourseBase(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    price: float
    status: CourseStatus
    author_id: Optional[int] = None
    category: Optional[CategoryBase] = None
    lessons: List[LessonBase] = Field(default_factory=list)
    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    title: str
    description: Optional[str] = None
    price: float = Field(ge=0)
    category_id: int = Field(ge=1)
    status: CourseStatus = CourseStatus.DRAFT


class CourseResponse(BaseModel):
    data: List[CourseBase]
    count: int
    page: int
    page_size: int
