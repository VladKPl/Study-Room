from app.models import Category, Course, CourseStatus


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


def test_soft_delete_forbidden_for_student_and_allowed_for_author(client, db_session):
    category = Category(name="Data Science")
    db_session.add(category)
    db_session.flush()

    course = Course(
        title="ML Intro",
        description="course",
        price=120,
        category_id=category.id,
        status=CourseStatus.PUBLISHED,
        is_deleted=False,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response_forbidden = client.delete(
        f"/api/v1/courses/{course.id}",
        headers={"X-Role": "student"},
    )
    assert response_forbidden.status_code == 403

    response_ok = client.delete(
        f"/api/v1/courses/{course.id}",
        headers={"X-Role": "author"},
    )
    assert response_ok.status_code == 200

    db_session.refresh(course)
    assert course.is_deleted is True


def test_start_course_forbidden_for_guest_and_allowed_for_student(client, db_session):
    category = Category(name="Cloud")
    db_session.add(category)
    db_session.flush()

    course = Course(
        title="DevOps 101",
        description="course start",
        price=130,
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
