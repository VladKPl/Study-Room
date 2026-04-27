from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.editorjs import parse_editorjs_payload_for_response

from app.models.courses import (
    BlockContentType,
    BlockModerationStatus,
    CourseStatus,
    LessonContentType,
    LessonModerationStatus,
    MediaAssetStatus,
    MediaAssetType,
)


class LessonBase(BaseModel):
    id: int
    title: str
    content_type: LessonContentType
    content: Optional[str | dict[str, Any]] = None
    video_url: Optional[str] = None
    attachment_url: Optional[str] = None
    external_url: Optional[str] = None
    moderation_status: LessonModerationStatus
    position: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator("content", mode="before")
    @classmethod
    def _parse_editor_content(cls, value: Any) -> Any:
        return parse_editorjs_payload_for_response(value)


class LessonCreate(BaseModel):
    title: str
    content_type: LessonContentType = LessonContentType.TEXT
    content: Optional[str | dict[str, Any]] = None
    video_url: Optional[str] = None
    attachment_url: Optional[str] = None
    external_url: Optional[str] = None
    position: Optional[int] = Field(default=None, ge=1)


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    content_type: Optional[LessonContentType] = None
    content: Optional[str | dict[str, Any]] = None
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


class CourseSectionBase(BaseModel):
    id: int
    course_id: int
    title: str
    position: int
    model_config = ConfigDict(from_attributes=True)


class CourseSectionCreate(BaseModel):
    title: str
    position: Optional[int] = Field(default=None, ge=1)


class CourseBlockBase(BaseModel):
    id: int
    section_id: int
    content_type: BlockContentType
    position: int
    text_content: Optional[str | dict[str, Any]] = None
    video_url: Optional[str] = None
    file_asset_id: Optional[int] = None
    external_url: Optional[str] = None
    moderation_status: BlockModerationStatus
    model_config = ConfigDict(from_attributes=True)

    @field_validator("text_content", mode="before")
    @classmethod
    def _parse_editor_text_content(cls, value: Any) -> Any:
        return parse_editorjs_payload_for_response(value)


class CourseBlockCreate(BaseModel):
    content_type: BlockContentType = BlockContentType.TEXT
    position: Optional[int] = Field(default=None, ge=1)
    text_content: Optional[str | dict[str, Any]] = None
    video_url: Optional[str] = None
    file_asset_id: Optional[int] = Field(default=None, ge=1)
    external_url: Optional[str] = None


class CourseBlockUpdate(BaseModel):
    content_type: Optional[BlockContentType] = None
    position: Optional[int] = Field(default=None, ge=1)
    text_content: Optional[str | dict[str, Any]] = None
    video_url: Optional[str] = None
    file_asset_id: Optional[int] = Field(default=None, ge=1)
    external_url: Optional[str] = None


class SubmitBlockLinkRequest(BaseModel):
    external_url: str


class BlockModerationUpdate(BaseModel):
    moderation_status: BlockModerationStatus


class MediaUploadUrlRequest(BaseModel):
    asset_type: MediaAssetType
    mime_type: str
    size_bytes: int = Field(ge=1)
    filename: str


class MediaUploadUrlResponse(BaseModel):
    asset_id: int
    upload_url: str
    storage_url: str
    status: MediaAssetStatus


class MediaAssetBase(BaseModel):
    id: int
    asset_type: MediaAssetType
    mime_type: str
    size_bytes: int
    storage_url: str
    status: MediaAssetStatus
    model_config = ConfigDict(from_attributes=True)


class MediaStatusUpdate(BaseModel):
    status: MediaAssetStatus


class MediaAssetsResponse(BaseModel):
    data: List[MediaAssetBase]
    count: int
    page: int
    page_size: int


class CourseSectionWithBlocks(BaseModel):
    id: int
    course_id: int
    title: str
    position: int
    blocks: List[CourseBlockBase] = Field(default_factory=list)


class CourseEditorSectionsResponse(BaseModel):
    course_id: int
    sections: List[CourseSectionWithBlocks] = Field(default_factory=list)
