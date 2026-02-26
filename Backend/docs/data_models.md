# Описание моделей данных

## users

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `email` | `String` | нет | - | unique, index |
| `full_name` | `String` | нет | - | - |
| `role` | `Enum(userrole)` | нет | `student` | значения: `guest`, `student`, `author`, `admin` |

Примечания:
- Роль по умолчанию в БД для зарегистрированного аккаунта — `student`.
- Роль анонимного посетителя (`guest`) берётся из логики API (`X-Role` fallback), а не из записи в таблице `users`.

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
| `status` | `Enum(coursestatus)` | нет | `DRAFT` | значения: `DRAFT`, `PUBLISHED`, `HIDDEN`, `BANNED` |
| `is_deleted` | `Boolean` | нет | `false` | флаг soft delete |
| `category_id` | `Integer` | да | - | FK -> `categories.id` |
| `author_id` | `Integer` | да | - | FK -> `users.id`, владелец курса |

Индексы:
- `ix_courses_visible_status_price(status, is_deleted, price)`
- `ix_courses_title`

## lessons

| Поле | Тип | Null | По умолчанию | Ограничения |
|---|---|---|---|---|
| `id` | `Integer` | нет | serial | PK, index |
| `title` | `String` | нет | - | - |
| `video_url` | `String` | да | - | - |
| `course_id` | `Integer` | да | - | FK -> `courses.id` |

## Связи

- `Category (1) -> (N) Course`
- `Course (1) -> (N) Lesson`
- `User (1) -> (N) Course`

В ORM:
- `Category.courses` <-> `Course.category`
- `Course.lessons` <-> `Lesson.course`
- для `Course.lessons` включён каскад `all, delete-orphan`.
- `User.courses` <-> `Course.author`

## Валидация на уровне API

- Ограничения query-параметров в list endpoint:
  - `min_price >= 0`
  - `max_price >= 0`
  - `page >= 1`
  - `1 <= page_size <= 100`
  - `sort` соответствует `price_asc|price_desc`
- RBAC по ролям:
  - `guest`: только чтение
  - `student`: может начать курс
  - `author`: может создавать курс и изменять только свои курсы
  - `admin`: полный доступ к модерации
- Для author-операций используется заголовок `X-User-Id`
  (временная идентификация до внедрения полноценной аутентификации).
