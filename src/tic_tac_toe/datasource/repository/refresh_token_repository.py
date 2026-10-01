from typing import Optional
from uuid import UUID

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
