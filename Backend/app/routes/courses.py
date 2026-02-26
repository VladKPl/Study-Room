from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.courses import Course, CourseStatus
from app.models.users import UserRole
from app.repositories.courses import CourseRepository
from app.schemas.courses import CourseBase, CourseResponse
from app.security.rbac import require_roles

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
    _: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
):
    course = _get_active_course_or_404(db, course_id)
    course.is_deleted = True
    db.commit()
    return {"message": f"Course {course_id} moved to trash"}


@router.patch("/courses/{course_id}/hide")
def hide_course(
    course_id: int,
    db: Session = Depends(get_db),
    _: UserRole = Depends(require_roles(UserRole.AUTHOR, UserRole.ADMIN)),
):
    course = _get_active_course_or_404(db, course_id)
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
