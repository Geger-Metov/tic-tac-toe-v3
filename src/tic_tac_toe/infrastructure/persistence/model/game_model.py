from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql.json import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from tic_tac_toe.infrastructure.database.base import Base


class GameStatus(str, Enum):
    """Зеркалит domain.model.game_state.GameState один в один — это его
    представление на уровне БД (persistence concern, поэтому живёт здесь,
    а не в domain)."""
    WAITING_FOR_PLAYER = "WAITING_FOR_PLAYER"
    PLAYER_TURN = "PLAYER_TURN"
    DRAW = "DRAW"
    WIN = "WIN"


class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    # Доска хранится как JSON (List[List[int]]); нормализовывать в отдельную
    # таблицу клеток избыточно — доска всегда читается/пишется целиком.
    board: Mapped[list] = mapped_column(JSONB, nullable=False)

    player_x_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    # NULL — ждём второго игрока; COMPUTER_ID (nil UUID) — играем с компьютером;
    # иначе — UUID присоединившегося игрока. См. domain.model.game.
    player_o_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus, name="game_status"), nullable=False
    )
    # UUID, привязанный к текущему статусу: для PLAYER_TURN — чей ход,
    # для WIN — победитель; для WAITING_FOR_PLAYER/DRAW всегда NULL.
    # Разложение GameState (sum type в domain) на пару колонок (status,
    # status_player_id) — ответственность мапера (datasource/mapper).
    status_player_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    # server_default нужен не приложению (оно всегда передаёт значение явно),
    # а миграции: добавить NOT NULL колонку в таблицу, где уже есть строки,
    # можно только если у колонки есть значение по умолчанию для них.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
