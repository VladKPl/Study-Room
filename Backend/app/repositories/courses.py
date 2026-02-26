from app.models.courses import Course, CourseStatus
from sqlalchemy.orm import Session, joinedload


class CourseRepository:
    @staticmethod
    def get_courses(
        db: Session, 
        q: str = None, 
        min_price: float = None, 
        max_price: float = None, 
        sort: str = "price_asc",
        page: int = 1,
        page_size: int = 10
    ):
        
        query = db.query(Course).filter(
            Course.is_deleted == False,
            Course.status == CourseStatus.PUBLISHED
        ).options(
            joinedload(Course.category), 
            joinedload(Course.lessons)
        )

        if q:
            query = query.filter(Course.title.ilike(f"%{q}%"))

        if min_price is not None:
            query = query.filter(Course.price >= min_price)
        if max_price is not None:
            query = query.filter(Course.price <= max_price)

        if sort == "price_asc":
            query = query.order_by(Course.price.asc())
        elif sort == "price_desc":
            query = query.order_by(Course.price.desc())

        count = query.count()
  
        offset = (page - 1) * page_size
        data = query.offset(offset).limit(page_size).all()

        return data, count
    