import sys
from pathlib import Path
from typing import AsyncGenerator

# --- Гарантируем, что "import tic_tac_toe" сработает, даже если pythonpath
# --- из [tool.pytest.ini_options] в pyproject.toml по какой-то причине не
# --- применился (например, конфликтующий pytest.ini/setup.cfg где-то ещё,
# --- или неполная синхронизация pyproject.toml). Тот же приём, что и в
# --- migrations/env.py — не полагаемся на одну-единственную настройку.
_project_root = Path(__file__).resolve().parent.parent
_src = _project_root / "src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tic_tac_toe.infrastructure.database.config import get_database_url
from tic_tac_toe.infrastructure.database.session import get_db_session
from tic_tac_toe.main import create_app


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Один тест — одна внешняя транзакция, которая в конце теста откатывается.
    Это позволяет гонять тесты против той же БД, что у тебя в docker compose
    для разработки (см. .env), не оставляя после себя мусора и не требуя
    отдельной тестовой БД: реальный commit() внутри приложения (в проде — в
    get_db_session) на самом деле не долетает дальше savepoint'а внутри этой
    внешней, никогда не коммитящейся транзакции.

    ВАЖНО: перед запуском тестов на целевой БД уже должны быть применены
    миграции (uv run alembic upgrade head) — тесты сами схему не создают.
    """
    engine = create_async_engine(get_database_url())
    connection = await engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Обычный httpx-клиент, но без сети: ASGITransport вызывает приложение
    напрямую в процессе теста — не нужен ни поднятый uvicorn, ни /docs,
    ни реальный порт. get_db_session подменён на фикстуру db_session, поэтому
    все запросы через этот клиент используют одну и ту же тестовую транзакцию.
    """
    app = create_app()

    async def override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
