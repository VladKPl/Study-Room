from app.models import (
    Category,
    Course,
    CourseStatus,
    Lesson,
    LessonContentType,
    LessonModerationStatus,
    User,
    UserRole,
)
from app.security.auth import create_access_token


def _create_user(db_session, email: str, role: UserRole) -> User:
    user = User(email=email, full_name=email.split("@")[0], role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}


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


def test_invalid_authorization_header_returns_401(client):
    response = client.get("/api/v1/courses", headers={"Authorization": "Token abc"})
    assert response.status_code == 401


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
        headers=_auth_headers(author),
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
        headers=_auth_headers(author_other),
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
        headers=_auth_headers(_create_user(db_session, "student@example.com", UserRole.STUDENT)),
    )
    assert response_student.status_code == 200


def test_author_can_open_draft_course_in_editor_mode(client, db_session):
    category = Category(name="Editor")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "editor-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Draft Editable Course",
        description="editor",
        price=100,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response = client.get(
        f"/api/v1/courses/{course.id}/editor",
        headers=_auth_headers(author),
    )

    assert response.status_code == 200
    assert response.json()["id"] == course.id


def test_author_can_create_lesson_for_own_course(client, db_session):
    category = Category(name="LessonCreate")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "lesson-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Course With Lessons",
        description="editor",
        price=120,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response = client.post(
        f"/api/v1/courses/{course.id}/lessons",
        headers=_auth_headers(author),
        json={
            "title": "Intro Lesson",
            "content_type": "text",
            "content": "Welcome to the course",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Intro Lesson"
    assert payload["content_type"] == LessonContentType.TEXT.value
    assert payload["position"] == 1


def test_author_cannot_create_lesson_for_foreign_course(client, db_session):
    category = Category(name="ForeignCourse")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author_owner = _create_user(db_session, "lesson-owner@example.com", UserRole.AUTHOR)
    author_other = _create_user(db_session, "lesson-other@example.com", UserRole.AUTHOR)
    course = Course(
        title="Owner Course",
        description="owner",
        price=99,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author_owner.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    response = client.post(
        f"/api/v1/courses/{course.id}/lessons",
        headers=_auth_headers(author_other),
        json={"title": "Hacker Lesson", "content_type": "text", "content": "Nope"},
    )
    assert response.status_code == 404


def test_link_lesson_defaults_to_pending_and_admin_can_moderate(client, db_session):
    category = Category(name="Moderation")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "mod-author@example.com", UserRole.AUTHOR)
    admin = _create_user(db_session, "mod-admin@example.com", UserRole.ADMIN)

    course = Course(
        title="Link Course",
        description="link",
        price=80,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    create_response = client.post(
        f"/api/v1/courses/{course.id}/lessons",
        headers=_auth_headers(author),
        json={
            "title": "External Resource",
            "content_type": "link",
            "external_url": "https://example.com/resource",
        },
    )
    assert create_response.status_code == 201
    lesson_id = create_response.json()["id"]
    assert create_response.json()["moderation_status"] == LessonModerationStatus.PENDING.value

    moderate_response = client.patch(
        f"/api/v1/courses/{course.id}/lessons/{lesson_id}/link-moderation",
        headers=_auth_headers(admin),
        json={"moderation_status": "approved"},
    )
    assert moderate_response.status_code == 200
    assert moderate_response.json()["moderation_status"] == LessonModerationStatus.APPROVED.value


def test_non_admin_cannot_moderate_lesson_link(client, db_session):
    category = Category(name="ModerationDenied")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "mod2-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Denied Course",
        description="link denied",
        price=60,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.flush()

    lesson = Lesson(
        title="Link Lesson",
        course_id=course.id,
        content_type=LessonContentType.LINK,
        external_url="https://example.com",
        moderation_status=LessonModerationStatus.PENDING,
        position=1,
    )
    db_session.add(lesson)
    db_session.commit()
    db_session.refresh(lesson)

    response = client.patch(
        f"/api/v1/courses/{course.id}/lessons/{lesson.id}/link-moderation",
        headers=_auth_headers(author),
        json={"moderation_status": "approved"},
    )
    assert response.status_code == 403
