from abc import ABC, abstractmethod
from uuid import UUID

from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game import Game


class IGameService(ABC):
    """
    Интерфейс сузился по сравнению с Заданием 1: раньше наружу торчали
    низкоуровневые куски (validate_field/is_game_over/get_next_move/save_game),
    которые вызывающий код (route) сам собирал в нужном порядке. Теперь вся
    последовательность действий одного хода (проверка очереди → валидация →
    применение → возможный ответ компьютера) — внутренняя ответственность
    make_move(), а не route'а. Наружу остаются только те 5 операций, которые
    реально нужны веб-слою по ТЗ.
    """

    @abstractmethod
    async def create_game(self, creator_id: UUID, vs_computer: bool) -> Game:
        pass

    @abstractmethod
    async def get_game_by_id(self, id: UUID) -> Game:
        """Кидает GameNotFoundError, если игры с таким id нет."""
        pass

    @abstractmethod
    async def get_available_games(self) -> list[Game]:
        """Игры, ожидающие второго игрока-человека (не vs computer)."""
        pass

    @abstractmethod
    async def get_finished_games_by_user(self, user_id: UUID) -> list[Game]:
        """Завершённые (победа или ничья) игры, где пользователь был X или O."""
        pass

    @abstractmethod
    async def join_game(self, game_id: UUID, user_id: UUID) -> Game:
        """Кидает GameNotFoundError / GameNotJoinableError."""
        pass

    @abstractmethod
    async def make_move(self, game_id: UUID, user_id: UUID, new_board: Board) -> Game:
        """
        Кидает GameNotFoundError / NotParticipantError / InvalidTurnError /
        InvalidMoveError. Если после хода игрока очередь доходит до
        компьютера — компьютер тоже ходит внутри этого же вызова, клиент
        получает уже финальный результат за один запрос.
        """
        pass
