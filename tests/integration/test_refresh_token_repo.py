import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tic_tac_toe.datasource.repository.refresh_token_repository import RefreshTokenRepo
from tic_tac_toe.domain.model.refresh_token import RefreshTokenRecord
from tic_tac_toe.infrastructure.database.config import get_database_url
from tic_tac_toe.infrastructure.persistence.model.refresh_token_model import RefreshTokenModel


def _record(jti):
    return RefreshTokenRecord(
        jti=jti,
        user_id=uuid4(),
        used=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )


async def test_claim_succeeds_once_then_fails(db_session):
    repo = RefreshTokenRepo(db_session)
    jti = uuid4()
    await repo.save(_record(jti))

    assert await repo.mark_used_if_unused(jti) is True
    assert await repo.mark_used_if_unused(jti) is False


async def test_claim_unknown_token_fails(db_session):
    assert await RefreshTokenRepo(db_session).mark_used_if_unused(uuid4()) is False


async def test_concurrent_claims_have_exactly_one_winner():
    """
    Настоящая конкуренция: независимые сессии и соединения с реальными commit —
    поэтому здесь нельзя использовать откатываемую фикстуру db_session. Строка
    создаётся и в конце удаляется вручную, другие данные БД не затрагиваются.
    """
    engine = create_async_engine(get_database_url())
    factory = async_sessionmaker(engine, expire_on_commit=False)
    jti = uuid4()
    try:
        async with factory() as session:
            await RefreshTokenRepo(session).save(_record(jti))
            await session.commit()

        async def claim() -> bool:
            async with factory() as session:
                won = await RefreshTokenRepo(session).mark_used_if_unused(jti)
                await session.commit()
                return won

        results = await asyncio.gather(*[claim() for _ in range(8)])

        assert results.count(True) == 1
        assert results.count(False) == 7
    finally:
        async with factory() as session:
            await session.execute(delete(RefreshTokenModel).where(RefreshTokenModel.jti == jti))
            await session.commit()
        await engine.dispose()
