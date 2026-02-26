# Testing With PostgreSQL

## 1) Set test database URL

Use env var:

```powershell
$env:TEST_DATABASE_URL="postgresql://postgres:24163542@localhost:5432/studyroom_test"
```

Or put this value into your shell profile / CI secrets.

## 2) Apply migrations into test DB

```powershell
$env:DATABASE_URL=$env:TEST_DATABASE_URL
.\.venv\Scripts\alembic.exe upgrade head
```

## 3) Run tests

```powershell
pytest -q
```

Tests automatically use `TEST_DATABASE_URL` and truncate tables between cases.
