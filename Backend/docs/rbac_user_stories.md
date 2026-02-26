# RBAC And User Stories

## Roles

- `student`: can view published courses.
- `author`: can view published courses and hide/soft-delete own content.
- `admin`: full moderation access, including ban and hard delete.

## Permissions Matrix

| Action | student | author | admin |
|---|---|---|---|
| List published courses (`GET /api/v1/courses`) | yes | yes | yes |
| Soft delete course (`DELETE /api/v1/courses/{id}`) | no | yes | yes |
| Hide course (`PATCH /api/v1/courses/{id}/hide`) | no | yes | yes |
| Ban course (`PATCH /api/v1/courses/{id}/ban`) | no | no | yes |
| Hard delete course (`DELETE /api/v1/courses/{id}/hard-delete`) | no | no | yes |

## User Stories

1. As a `student`, I want to browse published courses, so that I can choose what to learn.
2. As an `author`, I want to hide my course from listing, so that I can temporarily remove it from public view.
3. As an `author`, I want to move my course to trash (soft delete), so that I can recover it later if needed.
4. As an `admin`, I want to ban violating courses, so that policy-breaking content is not visible.
5. As an `admin`, I want to hard delete illegal or broken courses, so that the system remains clean.

## Technical Notes

- Current API uses header-based role simulation via `X-Role` for RBAC checks.
- In production this must be replaced with authenticated identity (JWT/session) and ownership checks.
