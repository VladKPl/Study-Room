from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.courses import Course, CourseStatus


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
        filters = [
            Course.is_deleted.is_(False),
            Course.status == CourseStatus.PUBLISHED,
        ]

        if q:
            filters.append(Course.title.ilike(f"%{q}%"))

        if min_price is not None:
            filters.append(Course.price >= min_price)
        if max_price is not None:
            filters.append(Course.price <= max_price)

        query = db.query(Course).filter(*filters)

        if sort == "price_asc":
            query = query.order_by(Course.price.asc())
        elif sort == "price_desc":
            query = query.order_by(Course.price.desc())

        count = (
            db.query(func.count(Course.id))
            .select_from(Course)
            .filter(*filters)
            .scalar()
            or 0
        )

        offset = (page - 1) * page_size
        data = query.options(
            joinedload(Course.category),
            selectinload(Course.lessons),
        ).offset(offset).limit(page_size).all()

        return data, count
