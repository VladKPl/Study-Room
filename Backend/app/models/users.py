import enum

from sqlalchemy import Column, Enum, Integer, String, text
from sqlalchemy.orm import relationship

from app.database import Base


class UserRole(str, enum.Enum):
    GUEST = "guest"
    STUDENT = "student"
    AUTHOR = "author"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda roles: [role.value for role in roles],
        ),
        default=UserRole.STUDENT,
        server_default=text("'student'"),
        nullable=False,
    )
    courses = relationship("Course", back_populates="author")
