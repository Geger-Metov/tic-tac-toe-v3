from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game_state import GameState, PlayerTurn, WaitingForPlayer

# Значения клеток на доске: см. Board — 0 пусто, 1 — X, -1 — O.
X_SYMBOL = 1
O_SYMBOL = -1

# Зарезервированный UUID для "компьютера" как участника игры — это nil UUID
# (RFC 4122 §4.1.7: все биты нулевые). uuid4() никогда не сгенерирует такое
# значение случайно, поэтому коллизий с настоящими пользователями не бывает.
# Благодаря этому GameState (PlayerTurn/Win) может всегда хранить обычный UUID,
# не заводя отдельную ветку "а может, это был компьютер" в каждом месте, где
# используется победитель/чей сейчас ход.
COMPUTER_ID: UUID = UUID(int=0)


@dataclass
class Game:
    id: UUID
    board: Board
    player_x_id: UUID
    # None — ждём второго игрока-человека; COMPUTER_ID — играем с компьютером;
    # иначе — UUID второго игрока-человека, который уже присоединился.
    player_o_id: Optional[UUID]
    state: GameState

    @classmethod
    def create_new(cls, creator_id: UUID, vs_computer: bool) -> "Game":
        """Создатель всегда играет за X. Если соперник — компьютер, он сразу
        занимает слот O и создатель сразу же может ходить; если соперник —
        человек, слот O пустует до join_game()."""
        if vs_computer:
            return cls(
                id=uuid4(),
                board=Board.create_empty(),
                player_x_id=creator_id,
                player_o_id=COMPUTER_ID,
                state=PlayerTurn(creator_id),
            )
        return cls(
            id=uuid4(),
            board=Board.create_empty(),
            player_x_id=creator_id,
            player_o_id=None,
            state=WaitingForPlayer(),
        )

    @property
    def is_vs_computer(self) -> bool:
        return self.player_o_id == COMPUTER_ID

    def is_participant(self, user_id: UUID) -> bool:
        return user_id == self.player_x_id or user_id == self.player_o_id

    def symbol_for(self, user_id: UUID) -> int:
        """Кидает ValueError, если user_id не участвует в этой игре."""
        if user_id == self.player_x_id:
            return X_SYMBOL
        if user_id == self.player_o_id:
            return O_SYMBOL
        raise ValueError(f"User {user_id} is not a participant of game {self.id}")

    def opponent_of(self, user_id: UUID) -> Optional[UUID]:
        if user_id == self.player_x_id:
            return self.player_o_id
        if user_id == self.player_o_id:
            return self.player_x_id
        return None
