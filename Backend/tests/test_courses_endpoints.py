from app.models import (
    BlockContentType,
    BlockModerationStatus,
    Category,
    Course,
    CourseBlock,
    CourseSection,
    CourseStatus,
    Lesson,
    LessonContentType,
    LessonModerationStatus,
    MediaAssetStatus,
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


def test_author_can_create_section_and_block(client, db_session):
    category = Category(name="Sections")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "section-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Section Course",
        description="sections",
        price=70,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.commit()
    db_session.refresh(course)

    section_response = client.post(
        f"/api/v1/courses/{course.id}/sections",
        headers=_auth_headers(author),
        json={"title": "Getting Started"},
    )
    assert section_response.status_code == 201
    section_id = section_response.json()["id"]

    block_response = client.post(
        f"/api/v1/sections/{section_id}/blocks",
        headers=_auth_headers(author),
        json={"content_type": "text", "text_content": "Welcome"},
    )
    assert block_response.status_code == 201
    assert block_response.json()["content_type"] == "text"
    assert block_response.json()["text_content"] == "Welcome"


def test_author_can_update_block(client, db_session):
    category = Category(name="BlocksUpdate")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "block-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Block Course",
        description="blocks",
        price=55,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.flush()
    section = CourseSection(course_id=course.id, title="Part 1", position=1)
    db_session.add(section)
    db_session.flush()
    block = CourseBlock(section_id=section.id, content_type=BlockContentType.TEXT, text_content="Old text", position=1)
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    response = client.patch(
        f"/api/v1/blocks/{block.id}",
        headers=_auth_headers(author),
        json={"content_type": "video", "video_url": "https://cdn.example.com/video.mp4"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["content_type"] == "video"
    assert payload["video_url"] == "https://cdn.example.com/video.mp4"
    assert payload["text_content"] is None


def test_author_can_request_upload_url(client, db_session):
    author = _create_user(db_session, "asset-author@example.com", UserRole.AUTHOR)

    response = client.post(
        "/api/v1/media/upload-url",
        headers=_auth_headers(author),
        json={
            "asset_type": "file",
            "mime_type": "application/pdf",
            "size_bytes": 2048,
            "filename": "intro.pdf",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["asset_id"] > 0
    assert payload["status"] == MediaAssetStatus.PENDING.value
    assert payload["upload_url"]
    assert payload["storage_url"]


def test_submit_link_and_admin_moderation_for_block(client, db_session):
    category = Category(name="LinkBlocks")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "link-author@example.com", UserRole.AUTHOR)
    admin = _create_user(db_session, "link-admin@example.com", UserRole.ADMIN)

    course = Course(
        title="Link Block Course",
        description="link blocks",
        price=40,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.flush()
    section = CourseSection(course_id=course.id, title="Links", position=1)
    db_session.add(section)
    db_session.flush()
    block = CourseBlock(
        section_id=section.id,
        content_type=BlockContentType.TEXT,
        text_content="placeholder",
        position=1,
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    submit_response = client.post(
        f"/api/v1/blocks/{block.id}/submit-link",
        headers=_auth_headers(author),
        json={"external_url": "https://example.com/resource"},
    )
    assert submit_response.status_code == 200
    assert submit_response.json()["moderation_status"] == BlockModerationStatus.PENDING.value

    moderate_response = client.patch(
        f"/api/v1/moderation/links/{block.id}",
        headers=_auth_headers(admin),
        json={"moderation_status": "approved"},
    )
    assert moderate_response.status_code == 200
    assert moderate_response.json()["moderation_status"] == BlockModerationStatus.APPROVED.value


def test_non_admin_cannot_moderate_block_link(client, db_session):
    category = Category(name="LinkBlocksDenied")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "link-author-denied@example.com", UserRole.AUTHOR)
    course = Course(
        title="Denied Link Block Course",
        description="link blocks",
        price=45,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.flush()
    section = CourseSection(course_id=course.id, title="Denied", position=1)
    db_session.add(section)
    db_session.flush()
    block = CourseBlock(
        section_id=section.id,
        content_type=BlockContentType.LINK,
        external_url="https://example.com",
        moderation_status=BlockModerationStatus.PENDING,
        position=1,
    )
    db_session.add(block)
    db_session.commit()
    db_session.refresh(block)

    response = client.patch(
        f"/api/v1/moderation/links/{block.id}",
        headers=_auth_headers(author),
        json={"moderation_status": "approved"},
    )
    assert response.status_code == 403


def test_author_can_fetch_editor_sections_with_blocks(client, db_session):
    category = Category(name="EditorRead")
    db_session.add(category)
    db_session.commit()
    db_session.refresh(category)

    author = _create_user(db_session, "editor-read-author@example.com", UserRole.AUTHOR)
    course = Course(
        title="Editor Read Course",
        description="read structure",
        price=50,
        category_id=category.id,
        status=CourseStatus.DRAFT,
        is_deleted=False,
        author_id=author.id,
    )
    db_session.add(course)
    db_session.flush()

    section1 = CourseSection(course_id=course.id, title="Section 1", position=1)
    section2 = CourseSection(course_id=course.id, title="Section 2", position=2)
    db_session.add_all([section1, section2])
    db_session.flush()

    block1 = CourseBlock(section_id=section1.id, content_type=BlockContentType.TEXT, text_content="Intro", position=1)
    block2 = CourseBlock(
        section_id=section1.id,
        content_type=BlockContentType.VIDEO,
        video_url="https://cdn.example.com/lesson.mp4",
        position=2,
    )
    db_session.add_all([block1, block2])
    db_session.commit()

    response = client.get(
        f"/api/v1/courses/{course.id}/sections",
        headers=_auth_headers(author),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["course_id"] == course.id
    assert len(payload["sections"]) == 2
    assert payload["sections"][0]["title"] == "Section 1"
    assert len(payload["sections"][0]["blocks"]) == 2
    assert payload["sections"][0]["blocks"][0]["content_type"] == "text"
