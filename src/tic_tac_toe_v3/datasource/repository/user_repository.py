from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.model.user import User as DomainUser
from tic_tac_toe.datasource.mapper.user_data_mapper import to_data, to_domain
from tic_tac_toe.infrastructure.persistence.model.user_model import UserModel


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: DomainUser) -> None:
        await self._session.merge(to_data(user))

    async def find_by_login(self, login: str) -> Optional[DomainUser]:
        stmt = select(UserModel).where(UserModel.login == login)
        result = await self._session.execute(stmt)
        data_model = result.scalar_one_or_none()
        return to_domain(data_model) if data_model is not None else None

    async def find_by_id(self, id: UUID) -> Optional[DomainUser]:
        data_model = await self._session.get(UserModel, id)
        return to_domain(data_model) if data_model is not None else None
