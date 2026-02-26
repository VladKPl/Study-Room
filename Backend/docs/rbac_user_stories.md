# RBAC And User Stories

## Roles

- `guest`: anonymous visitor, read-only access to public courses.
- `student`: registered user, can start courses.
- `author`: student with author privileges, can hide/soft-delete own content.
- `admin`: full moderation access, including ban and hard delete.

## Permissions Matrix

| Action | guest | student | author | admin |
|---|---|---|---|---|
| List published courses (`GET /api/v1/courses`) | yes | yes | yes | yes |
| View course card (`GET /api/v1/courses/{id}`) | yes | yes | yes | yes |
| Start course (`POST /api/v1/courses/{id}/start`) | no | yes | yes | yes |
| Soft delete course (`DELETE /api/v1/courses/{id}`) | no | no | yes | yes |
| Hide course (`PATCH /api/v1/courses/{id}/hide`) | no | no | yes | yes |
| Ban course (`PATCH /api/v1/courses/{id}/ban`) | no | no | no | yes |
| Hard delete course (`DELETE /api/v1/courses/{id}/hard-delete`) | no | no | no | yes |

## User Stories

1. As a `guest`, I want to search and view course cards, so that I can evaluate content before registration.
2. As a `student`, I want to start a course, so that I can begin learning after registration.
3. As an `author`, I want to hide my course from listing, so that I can temporarily remove it from public view.
4. As an `author`, I want to move my course to trash (soft delete), so that I can recover it later if needed.
5. As an `admin`, I want to ban violating courses, so that policy-breaking content is not visible.
6. As an `admin`, I want to hard delete illegal or broken courses, so that the system remains clean.

## Planned (not implemented yet)

- Self-upgrade `student -> author` by the authenticated user.
- Authentication/identity layer (JWT/session) to replace header-only role simulation.

## Technical Notes

- Current API uses header-based role simulation via `X-Role` for RBAC checks.
- In production this must be replaced with authenticated identity (JWT/session) and ownership checks.
