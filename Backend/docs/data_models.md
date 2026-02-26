# Data Models

## users

| Field | Type | Null | Default | Constraints |
|---|---|---|---|---|
| `id` | `Integer` | no | serial | PK, index |
| `email` | `String` | no | - | unique, index |
| `full_name` | `String` | no | - | - |
| `role` | `Enum(userrole)` | no | `student` | values: `guest`, `student`, `author`, `admin` |

Notes:
- Default DB role for created account is `student`.
- Anonymous visitor role is `guest` and comes from API logic (`X-Role` fallback), not from persisted user row.

## categories

| Field | Type | Null | Default | Constraints |
|---|---|---|---|---|
| `id` | `Integer` | no | serial | PK, index |
| `name` | `String` | no | - | unique |

## courses

| Field | Type | Null | Default | Constraints |
|---|---|---|---|---|
| `id` | `Integer` | no | serial | PK, index |
| `title` | `String` | no | - | index |
| `description` | `Text` | yes | - | - |
| `price` | `Float` | no | - | - |
| `status` | `Enum(coursestatus)` | no | `DRAFT` | values: `DRAFT`, `PUBLISHED`, `HIDDEN`, `BANNED` |
| `is_deleted` | `Boolean` | no | `false` | soft delete flag |
| `category_id` | `Integer` | yes | - | FK -> `categories.id` |

Indexes:
- `ix_courses_visible_status_price(status, is_deleted, price)`
- `ix_courses_title`

## lessons

| Field | Type | Null | Default | Constraints |
|---|---|---|---|---|
| `id` | `Integer` | no | serial | PK, index |
| `title` | `String` | no | - | - |
| `video_url` | `String` | yes | - | - |
| `course_id` | `Integer` | yes | - | FK -> `courses.id` |

## Relationships

- `Category (1) -> (N) Course`
- `Course (1) -> (N) Lesson`

In ORM:
- `Category.courses` <-> `Course.category`
- `Course.lessons` <-> `Lesson.course`
- `Course.lessons` has cascade `all, delete-orphan`.

## API-Level Validation

- Query constraints for list endpoint:
  - `min_price >= 0`
  - `max_price >= 0`
  - `page >= 1`
  - `1 <= page_size <= 100`
  - `sort` matches `price_asc|price_desc`
- RBAC validation by role:
  - `guest`: read-only
  - `student`: can start course
  - `author`: can mutate author-level operations
  - `admin`: full moderation operations
