import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
db_url = os.getenv("DATABASE_URL")

def test_connection():
    if not db_url:
        print("Ошибка: DATABASE_URL не найден в файле .env")
        return

    engine = create_engine(db_url)
    try:
        # Пытаемся выполнить простейший запрос
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        print("Бэкенд успешно подключился к PostgreSQL.")
    except Exception as e:
        print(f"Ошибка подключения: {e}")

if __name__ == "__main__":
    test_connection()
