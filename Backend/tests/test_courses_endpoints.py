from app.models import Category, Course, CourseStatus


def test_list_courses_returns_only_published_not_deleted(client, db_session):
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

    response = client.get("/api/v1/courses", headers={"X-Role": "student"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["data"]) == 1
    assert payload["data"][0]["title"] == "Python Basics"


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
