# Описание моделей данных

## users

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `email` | `String` | нет | - | unique, index |
| `full_name` | `String` | нет | - | - |
| `password_hash` | `String` | да | - | для пользователя только с OAuth может быть `NULL` |
| `is_active` | `Boolean` | нет | `true` | - |
| `is_email_verified` | `Boolean` | нет | `false` | - |
| `created_at` | `DateTime(timezone=True)` | нет | `now()` | - |
| `updated_at` | `DateTime(timezone=True)` | нет | `now()` | - |
| `role` | `Enum(userrole)` | нет | `student` | `guest`, `student`, `author`, `admin` |

Примечания:
- При регистрации роль по умолчанию: `student`.
- `guest` не хранится как запись пользователя; это анонимный режим без токена.

## oauth_accounts

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `user_id` | `Integer` | нет | - | FK -> `users.id`, index, `ON DELETE CASCADE` |
| `provider` | `String(32)` | нет | - | index |
| `provider_user_id` | `String(255)` | нет | - | - |
| `provider_email` | `String` | да | - | - |
| `created_at` | `DateTime(timezone=True)` | нет | `now()` | - |

Уникальные ограничения:
- `uq_oauth_provider_uid` на (`provider`, `provider_user_id`)
- `uq_oauth_user_provider` на (`user_id`, `provider`)

## refresh_tokens

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `user_id` | `Integer` | нет | - | FK -> `users.id`, index, `ON DELETE CASCADE` |
| `token` | `String` | нет | - | unique |
| `expires_at` | `DateTime(timezone=True)` | нет | - | index |
| `revoked_at` | `DateTime(timezone=True)` | да | - | отметка отзыва |
| `created_at` | `DateTime(timezone=True)` | нет | `now()` | - |

## categories

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `name` | `String` | нет | - | unique |

## courses

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `title` | `String` | нет | - | index |
| `description` | `Text` | да | - | - |
| `price` | `Float` | нет | - | - |
| `status` | `Enum(coursestatus)` | нет | `DRAFT` | `DRAFT`, `PUBLISHED`, `HIDDEN`, `BANNED` |
| `is_deleted` | `Boolean` | нет | `false` | признак мягкого удаления |
| `category_id` | `Integer` | да | - | FK -> `categories.id` |
| `author_id` | `Integer` | да | - | FK -> `users.id`, index |

Индексы:
- `ix_courses_visible_status_price(status, is_deleted, price)`
- `ix_courses_title`
- `ix_courses_author_id`

## lessons

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `title` | `String` | нет | - | - |
| `video_url` | `String` | да | - | - |
| `course_id` | `Integer` | да | - | FK -> `courses.id` |

## Связи

- `User (1) -> (N) Course`
- `User (1) -> (N) OAuthAccount`
- `User (1) -> (N) RefreshToken`
- `Category (1) -> (N) Course`
- `Course (1) -> (N) Lesson`

ORM-связи:
- `User.courses` <-> `Course.author`
- `User.oauth_accounts` <-> `OAuthAccount.user`
- `User.refresh_tokens` <-> `RefreshToken.user`
- `Category.courses` <-> `Course.category`
- `Course.lessons` <-> `Lesson.course` (`cascade="all, delete-orphan"`)

## Базовая валидация API

- Параметры запроса списка курсов:
  - `min_price >= 0`
  - `max_price >= 0`
  - `page >= 1`
  - `1 <= page_size <= 100`
  - `sort` = `price_asc | price_desc`
- Роли и доступ:
  - `guest`: только чтение
  - `student`: может начинать курс
  - `author`: создает курсы и меняет только свои
  - `admin`: полный доступ к модерации
