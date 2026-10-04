from uuid import UUID
from typing import Optional
from sqlalchemy import or_, and_, select, cast, desc, union_all, func, Float
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.model.game import Game as DomainGame
from tic_tac_toe.domain.model.player_rating import PlayerRating
from tic_tac_toe.datasource.mapper.domain_data_mapper import to_data, to_domain
from tic_tac_toe.infrastructure.persistence.model.game_model import GameModel, GameStatus
from tic_tac_toe.infrastructure.persistence.model.user_model import UserModel


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

    async def find_top_players(self, n: int) -> list[PlayerRating]:
        """
        Топ-N игроков по доле побед — одним запросом, всё считает БД:

          1. "participation" — по одной строке на каждое участие в завершённой
             игре: игра как X плюс игра как O (UNION ALL), с исходом игры.
          2. Группируем по пользователю и считаем побед/поражений/ничьих
             через count(*) FILTER (WHERE ...).
          3. Сортируем по доле побед по убыванию и берём первые N.

        INNER JOIN с users исключает компьютер: его nil-UUID (COMPUTER_ID)
        в таблице users не существует, так что строки с ним отсеиваются сами.
        Игроки без единой завершённой игры в выборку тоже не попадают —
        коэффициент у них не определён.
        """
        finished = [GameStatus.WIN, GameStatus.DRAW]

        as_x = select(
            GameModel.player_x_id.label("user_id"),
            GameModel.status.label("status"),
            GameModel.status_player_id.label("winner_id"),
        ).where(GameModel.status.in_(finished))

        as_o = select(
            GameModel.player_o_id.label("user_id"),
            GameModel.status.label("status"),
            GameModel.status_player_id.label("winner_id"),
        ).where(GameModel.status.in_(finished), GameModel.player_o_id.is_not(None))

        participation = union_all(as_x, as_o).subquery("participation")
        p = participation.c

        wins = func.count().filter(and_(p.status == GameStatus.WIN, p.winner_id == p.user_id))
        losses = func.count().filter(and_(p.status == GameStatus.WIN, p.winner_id != p.user_id))
        draws = func.count().filter(p.status == GameStatus.DRAW)
        win_ratio = cast(wins, Float) / func.count()

        stmt = (
            select(
                UserModel.id,
                UserModel.login,
                wins.label("wins"),
                losses.label("losses"),
                draws.label("draws"),
            )
            .select_from(participation.join(UserModel, UserModel.id == p.user_id))
            .group_by(UserModel.id, UserModel.login)
            # При равной доле — у кого больше побед, затем по логину: порядок
            # детерминирован, а не зависит от того, как БД решит раскладывать строки.
            .order_by(desc(win_ratio), desc(wins), UserModel.login)
            .limit(n)
        )
        result = await self._session.execute(stmt)
        return [
            PlayerRating(user_id=user_id, login=login, wins=w, losses=l, draws=d)
            for user_id, login, w, l, d in result.all()
        ]
