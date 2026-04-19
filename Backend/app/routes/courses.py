import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import get_db
from app.models.courses import (
    BlockContentType,
    BlockModerationStatus,
    Category,
    Course,
    CourseBlock,
    CourseSection,
    CourseStatus,
    Lesson,
    LessonContentType,
    LessonModerationStatus,
    MediaAsset,
    MediaAssetStatus,
)
from app.models.users import UserRole
from app.repositories.courses import CourseRepository
from app.schemas.courses import (
    BlockModerationUpdate,
    CourseBase,
    CourseBlockBase,
    CourseBlockCreate,
    CourseBlockUpdate,
    CourseCreate,
    CourseResponse,
    CourseSectionBase,
    CourseSectionCreate,
    LessonBase,
    LessonCreate,
    LessonModerationUpdate,
    LessonUpdate,
    MediaUploadUrlRequest,
    MediaUploadUrlResponse,
    SubmitBlockLinkRequest,
)
from app.security.rbac import get_current_user_id, require_roles

router = APIRouter()


def _get_active_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_deleted.is_(False),
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _get_public_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(
        Course.id == course_id,
        Course.is_deleted.is_(False),
        Course.status == CourseStatus.PUBLISHED,
    ).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _require_user_id_for_author(role: UserRole, user_id: int | None) -> int | None:
    if role == UserRole.AUTHOR and user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required for author operations",
        )
    return user_id


def _get_owner_mutable_course_or_404(
    db: Session,
    course_id: int,
    role: UserRole,
    user_id: int | None,
) -> Course:
    query = db.query(Course).filter(
        Course.id == course_id,
        Course.is_deleted.is_(False),
    )
    if role == UserRole.AUTHOR:
        query = query.filter(Course.author_id == user_id)
    course = query.first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _get_owner_mutable_section_or_404(
    db: Session,
    section_id: int,
    role: UserRole,
    user_id: int | None,
) -> CourseSection:
    query = db.query(CourseSection).join(Course, CourseSection.course_id == Course.id).filter(
        CourseSection.id == section_id,
        Course.is_deleted.is_(False),
    )
    if role == UserRole.AUTHOR:
        query = query.filter(Course.author_id == user_id)
    section = query.first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return section


def _get_owner_mutable_block_or_404(
    db: Session,
    block_id: int,
    role: UserRole,
    user_id: int | None,
) -> CourseBlock:
    query = (
        db.query(CourseBlock)
        .join(CourseSection, CourseBlock.section_id == CourseSection.id)
        .join(Course, CourseSection.course_id == Course.id)
        .filter(
            CourseBlock.id == block_id,
            Course.is_deleted.is_(False),
        )
    )
    if role == UserRole.AUTHOR:
        query = query.filter(Course.author_id == user_id)
    block = query.first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    return block


def _get_owner_mutable_lesson_or_404(
    db: Session,
    course_id: int,
    lesson_id: int,
    role: UserRole,
    user_id: int | None,
) -> Lesson:
    _get_owner_mutable_course_or_404(db, course_id, role, user_id)
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.course_id == course_id,
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson


def _next_lesson_position(db: Session, course_id: int) -> int:
    current_max = db.query(func.max(Lesson.position)).filter(Lesson.course_id == course_id).scalar()
    return (current_max or 0) + 1


def _next_section_position(db: Session, course_id: int) -> int:
    current_max = db.query(func.max(CourseSection.position)).filter(CourseSection.course_id == course_id).scalar()
    return (current_max or 0) + 1


def _next_block_position(db: Session, section_id: int) -> int:
    current_max = db.query(func.max(CourseBlock.position)).filter(CourseBlock.section_id == section_id).scalar()
    return (current_max or 0) + 1


def _apply_lesson_content_rules(lesson: Lesson) -> None:
    if lesson.content_type == LessonContentType.LINK:
        if not lesson.external_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="external_url is required for link lessons",
            )
        if lesson.moderation_status == LessonModerationStatus.NOT_REQUIRED:
            lesson.moderation_status = LessonModerationStatus.PENDING
    else:
        lesson.external_url = None
        lesson.moderation_status = LessonModerationStatus.NOT_REQUIRED

    if lesson.content_type != LessonContentType.VIDEO:
        lesson.video_url = None
    if lesson.content_type != LessonContentType.FILE:
        lesson.attachment_url = None


def _apply_block_content_rules(block: CourseBlock) -> None:
    if block.content_type == BlockContentType.LINK:
        if not block.external_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="external_url is required for link blocks",
            )
        if block.moderation_status == BlockModerationStatus.NOT_REQUIRED:
            block.moderation_status = BlockModerationStatus.PENDING
    else:
        block.external_url = None
        block.moderation_status = BlockModerationStatus.NOT_REQUIRED

    if block.content_type != BlockContentType.TEXT:
        block.text_content = None
    if block.content_type != BlockContentType.VIDEO:
        block.video_url = None
    if block.content_type != BlockContentType.FILE:
        block.file_asset_id = None
    elif block.file_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="file_asset_id is required for file blocks",
        )


@router.get("/courses", response_model=CourseResponse)
@router.get("/products", response_model=CourseResponse, include_in_schema=False)
def list_courses(
    q: str = Query(None, description="Search by title"),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    sort: str = Query("price_asc", pattern="^(price_asc|price_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: UserRole = Depends(
        require_roles(UserRole.GUEST, UserRole.STUDENT, UserRole.AUTHOR, UserRole.ADMIN)
    ),
):
    data, count = CourseRepository.get_courses(
        db,
        q=q,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return {
        "data": data,
        "count": count,
        "page": page,
        "page_size": page_size,
    }


@router.get("/courses/{course_id}", response_model=CourseBase)
def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db),
    _: UserRole = Depends(
        require_roles(UserRole.GUEST, UserRole.STUDENT, UserRole.AUTHOR, UserRole.ADMIN)
    ),
):
    return _get_public_course_or_404(db, course_id)


@router.get("/courses/{course_id}/editor", response_model=CourseBase)
def get_course_for_editor(
    course_id: int,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    return _get_owner_mutable_course_or_404(db, course_id, role, user_id)


@router.post("/courses", response_model=CourseBase)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)

    category = db.query(Category).filter(Category.id == payload.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    course = Course(
        title=payload.title,
        description=payload.description,
        price=payload.price,
        status=payload.status,
        is_deleted=False,
        category_id=payload.category_id,
        author_id=user_id,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.post("/courses/{course_id}/sections", response_model=CourseSectionBase, status_code=status.HTTP_201_CREATED)
def create_course_section(
    course_id: int,
    payload: CourseSectionCreate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    _get_owner_mutable_course_or_404(db, course_id, role, user_id)

    section = CourseSection(
        course_id=course_id,
        title=payload.title,
        position=payload.position or _next_section_position(db, course_id),
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.post("/sections/{section_id}/blocks", response_model=CourseBlockBase, status_code=status.HTTP_201_CREATED)
def create_course_block(
    section_id: int,
    payload: CourseBlockCreate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    section = _get_owner_mutable_section_or_404(db, section_id, role, user_id)

    if payload.file_asset_id is not None:
        asset = db.query(MediaAsset).filter(MediaAsset.id == payload.file_asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Media asset not found")
        if role == UserRole.AUTHOR and asset.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Media asset does not belong to current author")

    block = CourseBlock(
        section_id=section.id,
        content_type=payload.content_type,
        position=payload.position or _next_block_position(db, section.id),
        text_content=payload.text_content,
        video_url=payload.video_url,
        file_asset_id=payload.file_asset_id,
        external_url=payload.external_url,
        moderation_status=BlockModerationStatus.NOT_REQUIRED,
    )
    _apply_block_content_rules(block)
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.patch("/blocks/{block_id}", response_model=CourseBlockBase)
def update_course_block(
    block_id: int,
    payload: CourseBlockUpdate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    block = _get_owner_mutable_block_or_404(db, block_id, role, user_id)

    updates = payload.model_dump(exclude_unset=True)
    if "file_asset_id" in updates and updates["file_asset_id"] is not None:
        asset = db.query(MediaAsset).filter(MediaAsset.id == updates["file_asset_id"]).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Media asset not found")
        if role == UserRole.AUTHOR and asset.owner_id != user_id:
            raise HTTPException(status_code=403, detail="Media asset does not belong to current author")

    for field, value in updates.items():
        setattr(block, field, value)
    _apply_block_content_rules(block)
    db.commit()
    db.refresh(block)
    return block


@router.post("/media/upload-url", response_model=MediaUploadUrlResponse, status_code=status.HTTP_201_CREATED)
def create_media_upload_url(
    payload: MediaUploadUrlRequest,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    object_key = f"{user_id}/{uuid.uuid4()}-{payload.filename}"
    storage_url = f"https://cdn.studyroom.local/{object_key}"

    asset = MediaAsset(
        owner_id=user_id,
        asset_type=payload.asset_type,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        storage_url=storage_url,
        status=MediaAssetStatus.PENDING,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)

    upload_url = f"https://upload.studyroom.local/{object_key}?asset_id={asset.id}"
    return MediaUploadUrlResponse(
        asset_id=asset.id,
        upload_url=upload_url,
        storage_url=storage_url,
        status=asset.status,
    )


@router.post("/blocks/{block_id}/submit-link", response_model=CourseBlockBase)
def submit_block_link(
    block_id: int,
    payload: SubmitBlockLinkRequest,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    block = _get_owner_mutable_block_or_404(db, block_id, role, user_id)
    block.content_type = BlockContentType.LINK
    block.external_url = payload.external_url
    block.moderation_status = BlockModerationStatus.PENDING
    _apply_block_content_rules(block)
    db.commit()
    db.refresh(block)
    return block


@router.patch("/moderation/links/{block_id}", response_model=CourseBlockBase)
def moderate_link_block(
    block_id: int,
    payload: BlockModerationUpdate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN)),
):
    block = db.query(CourseBlock).filter(CourseBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.content_type != BlockContentType.LINK:
        raise HTTPException(status_code=400, detail="Only link blocks can be moderated")
    if payload.moderation_status not in (
        BlockModerationStatus.APPROVED,
        BlockModerationStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="moderation_status must be approved or rejected",
        )
    block.moderation_status = payload.moderation_status
    db.commit()
    db.refresh(block)
    return block


@router.post("/courses/{course_id}/lessons", response_model=LessonBase, status_code=status.HTTP_201_CREATED)
def create_lesson(
    course_id: int,
    payload: LessonCreate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    _get_owner_mutable_course_or_404(db, course_id, role, user_id)
    lesson = Lesson(
        course_id=course_id,
        title=payload.title,
        content_type=payload.content_type,
        content=payload.content,
        video_url=payload.video_url,
        attachment_url=payload.attachment_url,
        external_url=payload.external_url,
        moderation_status=LessonModerationStatus.NOT_REQUIRED,
        position=payload.position or _next_lesson_position(db, course_id),
    )
    _apply_lesson_content_rules(lesson)
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.patch("/courses/{course_id}/lessons/{lesson_id}", response_model=LessonBase)
def update_lesson(
    course_id: int,
    lesson_id: int,
    payload: LessonUpdate,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    lesson = _get_owner_mutable_lesson_or_404(db, course_id, lesson_id, role, user_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(lesson, field, value)
    _apply_lesson_content_rules(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


@router.delete("/courses/{course_id}/lessons/{lesson_id}")
def delete_lesson(
    course_id: int,
    lesson_id: int,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    lesson = _get_owner_mutable_lesson_or_404(db, course_id, lesson_id, role, user_id)
    db.delete(lesson)
    db.commit()
    return {"message": "Lesson deleted"}


@router.patch("/courses/{course_id}/lessons/{lesson_id}/link-moderation", response_model=LessonBase)
def moderate_lesson_link(
    course_id: int,
    lesson_id: int,
    payload: LessonModerationUpdate,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN)),
):
    lesson = db.query(Lesson).join(Course, Lesson.course_id == Course.id).filter(
        Lesson.id == lesson_id,
        Lesson.course_id == course_id,
        Course.is_deleted.is_(False),
    ).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    if lesson.content_type != LessonContentType.LINK:
        raise HTTPException(status_code=400, detail="Only link lessons can be moderated")
    if payload.moderation_status not in (
        LessonModerationStatus.APPROVED,
        LessonModerationStatus.REJECTED,
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="moderation_status must be approved or rejected",
        )
    lesson.moderation_status = payload.moderation_status
    db.commit()
    db.refresh(lesson)
    return lesson


@router.post("/courses/{course_id}/start")
def start_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.STUDENT, UserRole.AUTHOR, UserRole.ADMIN)),
):
    _get_public_course_or_404(db, course_id)
    return {"message": f"Course {course_id} started"}


@router.delete("/courses/{course_id}")
@router.delete("/products/{course_id}", include_in_schema=False)
def soft_delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    course = _get_owner_mutable_course_or_404(db, course_id, role, user_id)
    course.is_deleted = True
    db.commit()
    return {"message": f"Course {course_id} moved to trash"}


@router.patch("/courses/{course_id}/hide")
def hide_course(
    course_id: int,
    db: Session = Depends(get_db),
    role: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
    user_id: int | None = Depends(get_current_user_id),
):
    user_id = _require_user_id_for_author(role, user_id)
    course = _get_owner_mutable_course_or_404(db, course_id, role, user_id)
    course.status = CourseStatus.HIDDEN
    db.commit()
    return {"message": "Course hidden"}


@router.patch("/courses/{course_id}/ban")
def ban_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN)),
):
    course = _get_active_course_or_404(db, course_id)
    course.status = CourseStatus.BANNED
    db.commit()
    return {"message": "Course banned"}


@router.delete("/courses/{course_id}/hard-delete")
def hard_delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.ADMIN)),
):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course does not exist")
    db.delete(course)
    db.commit()
    return {"message": "Course permanently deleted"}
