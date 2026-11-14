import asyncio
import logging
from datetime import timedelta

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.datasource.service.game_service_impl import GameService
from tic_tac_toe.infrastructure.database.config import get_database_url
from tic_tac_toe.infrastructure.tasks.celery_app import celery_app
from tic_tac_toe.infrastructure.tasks.celery_config import get_abandoned_game_max_age
from tic_tac_toe.infrastructure.tasks.names import CLEANUP_ABANDONED_GAMES

logger = logging.getLogger(__name__)


async def _cleanup_abandoned_games(max_age: timedelta) -> int:
    # Новый engine на каждый запуск, а не общий из database/session.py: задача
    # вызывается через asyncio.run(), то есть в каждом запуске свой event loop,
    # а соединения asyncpg привязаны к тому loop, где созданы. Общий пул
    # со второго запуска упал бы с "attached to a different loop". NullPool —
    # при запуске раз в час пул нам ни к чему.
    engine = create_async_engine(get_database_url(), poolclass=NullPool)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as session:
            service = GameService(GameRepo(session))
            deleted = await service.delete_abandoned_games(max_age)
            await session.commit()
            return deleted
    finally:
        await engine.dispose()


@celery_app.task(
    name=CLEANUP_ABANDONED_GAMES,
    # Временные сбои (например, БД перезапускается) переживаем повторами с
    # растущей паузой, но не бесконечно. Повтор безопасен: задача идемпотентна.
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_kwargs={"max_retries": 3},
)
def cleanup_abandoned_games() -> int:
    """Удаляет игры, ожидающие второго игрока дольше ABANDONED_GAME_MAX_AGE_HOURS."""
    deleted = asyncio.run(_cleanup_abandoned_games(get_abandoned_game_max_age()))
    logger.info("Removed %d abandoned waiting game(s)", deleted)
    return deleted
