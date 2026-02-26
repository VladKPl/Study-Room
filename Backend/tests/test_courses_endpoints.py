from app.models import Category, Course, CourseStatus, User, UserRole


def _create_user(db_session, email: str, role: UserRole) -> User:
    user = User(email=email, full_name=email.split("@")[0], role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_list_courses_defaults_to_guest_and_returns_only_published_not_deleted(client, db_session):
    category = Category(name="Programming")
    db_session.add(category)
    db_session.flush()

    db_session.add_all(
        [
            Course(
                title="Python Basics",
                description="pub",
                price=100,
                category_id=category.id,
                status=CourseStatus.PUBLISHED,
                is_deleted=False,
            ),
            Course(
                title="Draft Course",
                description="draft",
                price=80,
                category_id=category.id,
                status=CourseStatus.DRAFT,
                is_deleted=False,
            ),
            Course(
                title="Deleted Course",
                description="deleted",
                price=60,
                category_id=category.id,
                status=CourseStatus.PUBLISHED,
                is_deleted=True,
            ),
        ]
    )
    db_session.commit()

    response = client.get("/api/v1/courses")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["data"]) == 1
    assert payload["data"][0]["title"] == "Python Basics"


def test_guest_can_view_course_card(client, db_session):
    category = Category(name="Backend")
    db_session.add(category)
    db_session.flush()

    course = Course(
        title="FastAPI Starter",
        description="course card",
        price=90,
        category_id=category.id,
        status=CourseStatus.PUBLISHED,
        is_deleted=False,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response = client.get(f"/api/v1/courses/{course.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == course.id
    assert payload["title"] == "FastAPI Starter"


def test_author_can_create_course(client, db_session):
    category = Category(name="Data Science")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "author@example.com", UserRole.AUTHOR)

    response = client.post(
        "/api/v1/courses",
        headers={"X-Role": "author", "X-User-Id": str(author.id)},
        json={
            "title": "ML Intro",
            "description": "course",
            "price": 120,
            "category_id": category.id,
            "status": "published",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "ML Intro"
    assert payload["author_id"] == author.id


def test_author_cannot_soft_delete_foreign_course(client, db_session):
    category = Category(name="Cloud")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author_owner = _create_user(db_session, "owner@example.com", UserRole.AUTHOR)
    author_other = _create_user(db_session, "other@example.com", UserRole.AUTHOR)

    course = Course(
        title="DevOps 101",
        description="course",
        price=130,
        category_id=category.id,
        status=CourseStatus.PUBLISHED,
        is_deleted=False,
        author_id=author_owner.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response = client.delete(
        f"/api/v1/courses/{course.id}",
        headers={"X-Role": "author", "X-User-Id": str(author_other.id)},
    )
    assert response.status_code == 404


def test_start_course_forbidden_for_guest_and_allowed_for_student(client, db_session):
    category = Category(name="Security")
    db_session.add(category)
    db_session.flush()

    course = Course(
        title="AppSec Basics",
        description="course start",
        price=95,
        category_id=category.id,
        status=CourseStatus.PUBLISHED,
        is_deleted=False,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response_guest = client.post(f"/api/v1/courses/{course.id}/start")
    assert response_guest.status_code == 403

    response_student = client.post(
        f"/api/v1/courses/{course.id}/start",
        headers={"X-Role": "student"},
    )
    assert response_student.status_code == 200
