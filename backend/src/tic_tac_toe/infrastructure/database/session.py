from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from tic_tac_toe.infrastructure.database.config import get_database_url

engine: AsyncEngine = create_async_engine(get_database_url(), echo=False)

# expire_on_commit=False: после commit() атрибуты объектов остаются доступны без
# повторного похода в БД — удобно, т.к. мы дальше мапим объект обратно в domain-модель.
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI-зависимость: одна Session на один HTTP-запрос.

    Здесь же и решается вопрос "кто отвечает за commit/rollback":
    сама Session создаётся и закрывается тут, а не в repository/service —
    так что вызывающий код (route/service/repository) просто работает
    с сессией, а транзакцией управляет эта зависимость.
    """
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# scope="function": код после yield (commit/rollback) выполняется сразу после
# обработчика, ДО отправки ответа. По умолчанию (scope="request") он идёт
# после отправки: клиент получал 2xx до коммита (последующий GET мог увидеть
# старое состояние), а ошибка коммита уже не могла стать ответом об ошибке.
# Во всех маршрутах и зависимостях брать сессию через этот алиас, а не через
# голый Depends(get_db_session).
DbSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]
