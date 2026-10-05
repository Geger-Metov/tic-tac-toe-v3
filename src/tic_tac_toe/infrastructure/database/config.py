import os

from tic_tac_toe.infrastructure.env import load_env

load_env()


def get_database_url() -> str:
    """
    Возвращает connection string для подключения к PostgreSQL.

    В Docker (см. compose.yaml) переменная DATABASE_URL приходит уже готовая:
        postgresql+asyncpg://user:password@db:5432/ttt_db

    Локально (не в контейнере) DATABASE_URL обычно не задана — тогда строка
    собирается из отдельных POSTGRES_* переменных, которые к этому моменту
    уже подхватились из .env (или остались на дефолтах — localhost).
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    user = os.getenv("POSTGRES_USER", "user")
    password = os.getenv("POSTGRES_PASSWORD", "user")
    db = os.getenv("POSTGRES_DB", "ttt_db")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")

    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
