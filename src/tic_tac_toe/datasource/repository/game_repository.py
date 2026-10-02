from uuid import UUID
from typing import Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.model.game import Game as DomainGame
from tic_tac_toe.datasource.mapper.domain_data_mapper import to_data, to_domain
from tic_tac_toe.infrastructure.persistence.model.game_model import GameModel, GameStatus


class GameRepo:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, game: DomainGame) -> None:
        data_model = to_data(game)
        # merge сам решает insert это или update по первичному ключу (id) —
        # нам не нужно отдельно различать "создание" и "обновление" игры.
        await self._session.merge(data_model)

    async def find_by_id(self, uuid: UUID) -> Optional[DomainGame]:
        data_model = await self._session.get(GameModel, uuid)
        if data_model is None:
            return None

        return to_domain(data_model)

    async def find_waiting_games(self) -> list[DomainGame]:
        stmt = select(GameModel).where(GameModel.status == GameStatus.WAITING_FOR_PLAYER)
        res = await self._session.execute(stmt)
        return [to_domain(model) for model in res.scalars().all()]

    async def find_finished_by_user(self, user_id: UUID) -> list[DomainGame]:
        """
        Завершённые игры пользователя (он X или O): статус WIN или DRAW.
        Сначала самые новые. Фильтрация целиком на стороне БД, а не в Python —
        иначе пришлось бы тянуть вообще все игры и отсеивать их в памяти.
        """
        stmt = (
            select(GameModel)
            .where(GameModel.status.in_([GameStatus.WIN, GameStatus.DRAW]))
            .where(or_(GameModel.player_x_id == user_id, GameModel.player_o_id == user_id))
            .order_by(GameModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [to_domain(model) for model in result.scalars().all()]
