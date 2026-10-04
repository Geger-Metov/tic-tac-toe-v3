from typing import Optional
from uuid import UUID
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.model.refresh_token import RefreshTokenRecord as DomainRefreshToken
from tic_tac_toe.datasource.mapper.refresh_token_data_mapper import to_data, to_domain
from tic_tac_toe.infrastructure.persistence.model.refresh_token_model import RefreshTokenModel


class RefreshTokenRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, record: DomainRefreshToken) -> None:
        await self._session.merge(to_data(record))

    async def find_by_jti(self, jti: UUID) -> Optional[DomainRefreshToken]:
        data_model = await self._session.get(RefreshTokenModel, jti)
        return to_domain(data_model) if data_model is not None else None

    async def mark_used_if_unused(self, jti: UUID) -> bool:
        """
        Атомарно "захватывает" refreshToken: True — этот вызов перевёл его из
        неиспользованного в использованный, False — токена нет либо он уже
        использован (в том числе параллельным запросом).

        Проверка и запись — ОДНА SQL-команда:
            UPDATE refresh_tokens SET used = true WHERE jti = :jti AND used = false
        Если сначала прочитать used, а потом отдельно записать, два одновременных
        запроса оба увидят used = false и оба получат новую пару токенов. Здесь
        же при конкуренции второй UPDATE дождётся первого (блокировка строки),
        перепроверит WHERE, увидит used = true и обновит 0 строк.
        """
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.jti == jti, RefreshTokenModel.used.is_(False))
            .values(used=True)
        )
        return result.rowcount == 1
