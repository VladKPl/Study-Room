# Тестирование с PostgreSQL

## 1) Укажите URL тестовой базы данных

Используйте переменную окружения:

```powershell
$env:TEST_DATABASE_URL="postgresql://<user>:<password>@localhost:5432/studyroom_test"
```

Либо сохраните это значение в профиле shell / секретах CI.

## 2) Примените миграции в тестовую БД

```powershell
$env:DATABASE_URL=$env:TEST_DATABASE_URL
.\.venv\Scripts\alembic.exe upgrade head
```

## 3) Запустите тесты

```powershell
pytest -q
```

Тесты автоматически используют `TEST_DATABASE_URL` и очищают таблицы между кейсами.

## 4) Демо-страница

Запустите API:

```powershell
uvicorn app.main:app --reload
```

Откройте:

- `http://127.0.0.1:8000/demo`

Переключайте роли (`guest`, `student`, `author`, `admin`) для проверки поведения RBAC.
Для операций автора дополнительно передайте `X-User-Id`.
