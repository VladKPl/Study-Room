# Study-Room

## 1. Описание проекта
`Study-Room` -  сервис, в котором различные пользователи могут создавать свои курсы и публиковать их на платформе.  
Репозиторий разделен на две части:
- `Backend` - серверная логика, API, база данных, авторизация и тесты.
- `Frontend` - клиентская часть приложения.

## 2. Основные возможности
- Регистрация и вход пользователей.
- JWT-аутентификация и refresh token механика.
- Вход через Google OAuth2.
- Ролевая модель доступа (RBAC): `guest`, `student`, `author`, `admin`.
- Каталог курсов: просмотр, фильтрация, сортировка.
- Редакторская часть: создание и управление курсами, уроками, секциями и блоками.
- Загрузка и модерация медиа-контента.
- Модерация ссылок и контента на уровне ролей.

## 3. Стек технологий
- Backend: Python, FastAPI, Uvicorn.
- База данных: PostgreSQL.
- ORM и миграции: SQLAlchemy, Alembic.
- Аутентификация и безопасность: JWT (`python-jose`), `passlib[bcrypt]`, OAuth2.
- Валидация и конфигурация: Pydantic, python-dotenv.
- Тестирование: pytest, FastAPI TestClient.
- Frontend: выделен отдельной директорией `Frontend` (часть проекта, находится в разработке).

## 4. Структура проекта
```text
Study-Room/
|-- Backend/
|   |-- app/                        # Исходный код backend
|   |-- alembic/                    # Миграции базы данных
|   |-- docs/                       # Техническая документация
|   |-- tests/                      # Автотесты
|   |-- requirements.txt
|   |-- .env.example
|   |-- .env.test.example
|-- Frontend/
|-- README.md
```

## 5. Переменные окружения проекта
Основные переменные backend-части (файл `Backend/.env`, создается из `Backend/.env.example`):

| Переменная | Назначение | Пример |
|---|---|---|
| `DATABASE_URL` | Подключение к основной БД PostgreSQL | `postgresql://user:password@localhost:5432/studyroom` |
| `TEST_DATABASE_URL` | Подключение к тестовой БД | `postgresql://user:password@localhost:5432/studyroom_test` |
| `BACKEND_CORS_ORIGINS` | Разрешенные CORS-источники | `http://localhost:5173,http://127.0.0.1:5173` |
| `JWT_SECRET` | Секретный ключ для JWT | `long-random-secret` |
| `JWT_ALGORITHM` | Алгоритм JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни access token | `30` |
| `REFRESH_TOKEN_EXPIRE_HOURS` | Время жизни refresh token | `36` |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID | `...` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret | `...` |
| `GOOGLE_REDIRECT_URI` | Callback URI для Google OAuth | `http://127.0.0.1:8000/api/v1/auth/google/callback` |

## 6. Как запустить проект
На текущем этапе полностью готов и запускается backend-часть.

1. Клонировать репозиторий:
```powershell
git clone https://github.com/VladKPl/Study-Room.git
cd Study-Room
```

2. Перейти в backend:
```powershell
cd Backend
```

3. Создать и активировать виртуальное окружение:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Установить зависимости:
```powershell
pip install -r requirements.txt
```

5. Создать файл окружения:
```powershell
Copy-Item .env.example .env
```

6. Применить миграции:
```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

7. Запустить сервер:
```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

8. Проверить API:
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
