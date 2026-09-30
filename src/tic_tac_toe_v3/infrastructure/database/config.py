import os
from pathlib import Path

from dotenv import load_dotenv


def _find_and_load_dotenv() -> None:
    """
    Ищет .env, поднимаясь от расположения ЭТОГО файла вверх, пока не найдёт
    либо сам .env, либо маркер корня проекта (pyproject.toml) — тот же приём,
    что уже используется в migrations/env.py и tests/conftest.py, чтобы не
    зависеть ни от текущей рабочей директории процесса (cwd), ни от того, в
    какой раскладке лежит пакет (локально src/tic_tac_toe, в Docker — плоско).

    В Docker-образе .env-файла обычно нет вообще (он в .dockerignore,
    реальные переменные приходят напрямую от docker compose через
    environment:) — тогда load_dotenv() просто ничего не находит и не
    делает, это ожидаемо и безопасно.

    load_dotenv() по умолчанию НЕ перезаписывает уже установленные
    переменные окружения (override=False) — значит, реальные переменные
    (от docker compose, от shell) всегда имеют приоритет над .env.
    """
    current = Path(__file__).resolve().parent
    for _ in range(6):  # разумный предел, чтобы не уйти в бесконечный подъём
        candidate = current / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
        if (current / "pyproject.toml").is_file():
            # дошли до корня проекта, но .env там нет — нормальная ситуация
            return
        current = current.parent


_find_and_load_dotenv()


def get_database_url() -> str:
    """
    Возвращает connection string для подключения к PostgreSQL.

    В Docker (см. compose.yaml) переменная DATABASE_URL приходит уже готовая:
        postgresql+asyncpg://user:password@db:5432/ttt_db

    Локально (не в контейнере) DATABASE_URL обычно не задана — тогда строка
    собирается из отдельных POSTGRES_* переменных, которые к этому моменту
    уже подхватились из .env выше (или остались на своих дефолтах, если
    файла .env вовсе нет — подключаемся к localhost).
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
