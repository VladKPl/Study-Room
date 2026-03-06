# Стек аутентификации

## Выбранный стек

- `SQLAlchemy` + `Alembic`: хранение пользователей и OAuth-идентичностей.
- `passlib[bcrypt]`: хеширование пароля.
- `bcrypt==4.1.3`: зафиксированная версия для совместимости с Python 3.13.
- `python-jose[cryptography]`: подпись и проверка JWT.
- `Authlib`: OAuth2/OpenID Connect клиент (Google как первый провайдер).
- `email-validator`: валидация email в Pydantic-схемах.

## Этап 1: модель данных (сделано)

- Расширена таблица `users`:
  - `password_hash`,
  - `is_active`,
  - `is_email_verified`,
  - `created_at`,
  - `updated_at`.
- Добавлена таблица `oauth_accounts`:
  - `user_id`,
  - `provider`,
  - `provider_user_id`,
  - `provider_email`,
  - уникальные ограничения по идентичности.

## Этап 2: базовые эндпоинты аутентификации (сделано)

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`

## Этап 3: RBAC через access token (сделано)

- Защищённые эндпоинты читают роль и `user_id` из `Authorization: Bearer <access_token>`.
- Без токена пользователь работает как `guest`.
- Проверка владения курсом для `author` строится на `current_user.id`.

## Этап 4: вход через Google OAuth (сделано)

- `GET /api/v1/auth/google/login`
- `GET /api/v1/auth/google/callback`
- После callback создаётся (или привязывается) локальный пользователь и выдаются локальные JWT-токены.
