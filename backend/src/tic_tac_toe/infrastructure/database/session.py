from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


# expire_on_commit=False: после commit() атрибуты объектов остаются доступны без
# повторного похода в БД — удобно, т.к. мы дальше мапим объект обратно в domain-модель.
def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """
    FastAPI-зависимость: одна Session на один HTTP-запрос.

    Здесь же и решается вопрос "кто отвечает за commit/rollback":
    сама Session создаётся и закрывается тут, а не в repository/service —
    так что вызывающий код (route/service/repository) просто работает
    с сессией, а транзакцией управляет эта зависимость.
    """
    sessionmaker = request.app.state.sessionmaker
    async with sessionmaker() as session:
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
