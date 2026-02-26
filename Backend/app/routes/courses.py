from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.repositories.courses import CourseRepository
from app.schemas.courses import CourseResponse
from app.models.courses import Course, CourseStatus # Добавили CourseStatus

router = APIRouter()

@router.get("/products", response_model=CourseResponse)
def list_products(
    q: str = Query(None, description="Поиск по названию"),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    sort: str = Query("price_asc", pattern="^(price_asc|price_desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    # Вызываем магию из репозитория
    data, count = CourseRepository.get_courses(
        db, q=q, min_price=min_price, max_price=max_price, 
        sort=sort, page=page, page_size=page_size
    )
    
    return {
        "data": data,
        "count": count,
        "page": page,
        "page_size": page_size
    }


@router.delete("/products/{course_id}")
def soft_delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    
    course.is_deleted = True
    db.commit()
    return {"message": f"Курс {course_id} перемещен в корзину"}

@router.patch("/courses/{course_id}/hide")
def hide_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    
    course.status = CourseStatus.HIDDEN
    db.commit()
    return {"message": "Курс скрыт автором"}

@router.patch("/courses/{course_id}/ban")
def ban_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id, Course.is_deleted == False).first()
    if not course:
        raise HTTPException(status_code=404, detail="Курс не найден")
    
    course.status = CourseStatus.BANNED
    db.commit()
    return {"message": "Курс заблокирован модератором"}

@router.delete("/courses/{course_id}/hard-delete")
def hard_delete_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Курс не существует")
    
    db.delete(course)
    db.commit()
    return {"message": "Курс полностью удален из системы"}