from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.database import get_db
from app.models.courses import (
    Category,
    Course,
    CourseStatus,
    Lesson,
    LessonContentType,
    LessonModerationStatus,
)
from app.models.users import UserRole
from app.repositories.courses import CourseRepository
from app.schemas.courses import (
    CourseBase,
    CourseCreate,
    CourseResponse,
    LessonBase,
    LessonCreate,
    LessonModerationUpdate,
    LessonUpdate,
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
