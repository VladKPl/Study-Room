import os
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

load_dotenv()

base_db_url = os.getenv("DATABASE_URL")
test_db_url = os.getenv("TEST_DATABASE_URL")
if not test_db_url:
    if not base_db_url:
        raise RuntimeError("Set DATABASE_URL or TEST_DATABASE_URL for tests")
    if "/" not in base_db_url:
        raise RuntimeError("DATABASE_URL is invalid")
    test_db_url = base_db_url.rsplit("/", 1)[0] + "/studyroom_test"

# Force app to initialize with test database.
os.environ["DATABASE_URL"] = test_db_url

from app.database import SessionLocal, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, Course, CourseStatus, Lesson, User  # noqa: E402,F401


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def override_get_db() -> Iterator[Session]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def apply_migrations() -> Iterator[None]:
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_db() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE lessons, courses, categories, users "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture()
def db_session() -> Iterator[Session]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
