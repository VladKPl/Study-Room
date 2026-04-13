# Тестирование с PostgreSQL

## 1. Создать тестовую базу

Пример: `studyroom_test`.

## 2. Настроить переменную окружения

В PowerShell:

```powershell
$env:TEST_DATABASE_URL="postgresql://<user>:<password>@localhost:5432/studyroom_test"
```

## 3. Применить миграции в тестовую БД

```powershell
$env:DATABASE_URL=$env:TEST_DATABASE_URL
.\.venv\Scripts\alembic.exe upgrade head
```

Проверка:

```powershell
.\.venv\Scripts\alembic.exe current
```

## 4. Запустить тесты

```powershell
$env:TEST_DATABASE_URL="postgresql://<user>:<password>@localhost:5432/studyroom_test"
.\.venv\Scripts\pytest.exe -q
```

## 5. Проверка аутентификации и RBAC вручную

1. Зарегистрировать пользователя:

```http
POST /api/v1/auth/register
```

2. Получить `access_token` и передавать его в заголовке:

```http
Authorization: Bearer <access_token>
```

3. Проверить ограничения ролей:
- без токена = `guest`,
- `student` не может создавать курс,
- `author` может создавать и редактировать только свои курсы,
- `admin` может выполнять модерацию (`ban`, `hard-delete`).

## 6. Проверка refresh-token revocation

1. Получить пару токенов через `POST /api/v1/auth/login` или `POST /api/v1/auth/register`.
2. Вызвать `POST /api/v1/auth/refresh` с текущим `refresh_token`.
3. Убедиться, что вернулся новый `refresh_token`.
4. Повторно вызвать `POST /api/v1/auth/refresh` со старым токеном:
   - ожидается `401` (токен уже revoked).
5. Вызвать `POST /api/v1/auth/logout` с access-токеном в `Authorization`.
6. Убедиться, что последующий `POST /api/v1/auth/refresh` возвращает `401`.

## 7. Проверка Google OAuth

1. Убедиться, что в `.env` заполнены:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `GOOGLE_REDIRECT_URI`
2. Перейти на:
   - `GET /api/v1/auth/google/login`
3. После успешного callback проверить, что API возвращает локальные `access_token`/`refresh_token`.
