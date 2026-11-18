from datetime import UTC, datetime, timedelta
from functools import cache
from uuid import UUID

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.domain.exception.game_exceptions import (
    GameNotFoundError,
    GameNotJoinableError,
    InvalidMoveError,
    InvalidTurnError,
    NotParticipantError,
)
from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game import COMPUTER_ID, O_SYMBOL, X_SYMBOL, Game
from tic_tac_toe.domain.model.game_state import Draw, GameState, PlayerTurn, Win
from tic_tac_toe.domain.model.player_rating import PlayerRating
from tic_tac_toe.domain.service.game_interface import IGameService

_WIN_SCORE = 10
_DRAW_SCORE = 0

# Клетки доски в плоском кортеже (индекс = строка * 3 + столбец) и все 8 линий.
_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def _winner(cells: tuple[int, ...]) -> int:
    for a, b, c in _LINES:
        if cells[a] != 0 and cells[a] == cells[b] == cells[c]:
            return cells[a]
    return 0


@cache
def _minimax_cached(cells: tuple[int, ...], depth: int, is_maximizing: bool) -> int:
    """
    Минимакс с мемоизацией по (позиция, глубина, чей ход). Всего позиций
    3^9 = 19683, поэтому кэш ограничен сверху и после первых партий ответ
    считается за микросекунды (без кэша первый ответ — около 60 тысяч узлов,
    ~180 мс, и всё это блокировало event loop). Результаты те же, что у
    наивного перебора: глубина входит в ключ, значит предпочтение быстрых побед
    сохраняется.
    """
    winner = _winner(cells)
    if winner == O_SYMBOL:
        return _WIN_SCORE - depth
    if winner == X_SYMBOL:
        return -_WIN_SCORE + depth
    if 0 not in cells:
        return _DRAW_SCORE

    symbol = O_SYMBOL if is_maximizing else X_SYMBOL
    scores = (
        _minimax_cached(cells[:i] + (symbol,) + cells[i + 1 :], depth + 1, not is_maximizing)
        for i, cell in enumerate(cells)
        if cell == 0
    )
    return max(scores) if is_maximizing else min(scores)


def _flatten(board: Board) -> tuple[int, ...]:
    return tuple(cell for row in board.grid for cell in row)


class GameService(IGameService):
    WIN_SCORE = _WIN_SCORE
    DRAW_SCORE = _DRAW_SCORE

    def __init__(self, repo: GameRepo) -> None:
        self._repo = repo

    # ---- публичный интерфейс -------------------------------------------------

    async def create_game(self, creator_id: UUID, vs_computer: bool) -> Game:
        game = Game.create_new(creator_id=creator_id, vs_computer=vs_computer)
        await self._repo.save(game)
        return game

    async def get_game_by_id(self, id: UUID) -> Game:
        game = await self._repo.find_by_id(id)
        if game is None:
            raise GameNotFoundError(f"Game with id {id} not found")
        return game

    async def get_available_games(self) -> list[Game]:
        return await self._repo.find_waiting_games()

    async def get_finished_games_by_user(self, user_id: UUID) -> list[Game]:
        return await self._repo.find_finished_by_user(user_id)

    async def get_top_players(self, n: int) -> list[PlayerRating]:
        if n < 1:
            return []
        return await self._repo.find_top_players(n)

    async def delete_abandoned_games(self, max_age: timedelta) -> int:
        cutoff = datetime.now(UTC) - max_age
        return await self._repo.delete_abandoned_waiting(cutoff)

    async def _get_game_for_update(self, id: UUID) -> Game:
        game = await self._repo.find_by_id_for_update(id)
        if game is None:
            raise GameNotFoundError(f"Game with id {id} not found")
        return game

    async def join_game(self, game_id: UUID, user_id: UUID) -> Game:
        # Блокировка строки: два одновременных join не должны оба «успеть».
        game = await self._get_game_for_update(game_id)

        if game.player_o_id is not None:
            raise GameNotJoinableError("Game is not waiting for a player")
        if game.player_x_id == user_id:
            raise GameNotJoinableError("Cannot join your own game")

        joined_game = Game(
            id=game.id,
            board=game.board,
            player_x_id=game.player_x_id,
            player_o_id=user_id,
            # Создатель (X) всегда ходит первым.
            state=PlayerTurn(game.player_x_id),
            created_at=game.created_at,
        )
        await self._repo.save(joined_game)
        return joined_game

    async def make_move(self, game_id: UUID, user_id: UUID, new_board: Board) -> Game:
        # Блокировка строки на всё время хода (вместе с ответом компьютера):
        # иначе два запроса с одной и той же доской (двойной клик) оба проходят
        # проверку, и второй затирает ход первого.
        game = await self._get_game_for_update(game_id)

        if not game.is_participant(user_id):
            raise NotParticipantError()

        if not (isinstance(game.state, PlayerTurn) and game.state.player_id == user_id):
            raise InvalidTurnError()

        if not self._validate_move(game, user_id, new_board):
            raise InvalidMoveError()

        game = self._apply_move(game, new_board, user_id)
        await self._repo.save(game)

        # Если очередь дошла до компьютера — считаем его ответ сразу же,
        # синхронно, внутри этого же запроса: клиент никогда не увидит
        # промежуточное состояние PlayerTurn(COMPUTER_ID) и не должен сам
        # отдельно "запрашивать ход компьютера".
        if isinstance(game.state, PlayerTurn) and game.state.player_id == COMPUTER_ID:
            computer_board = self._compute_best_move(game.board)
            game = self._apply_move(game, computer_board, COMPUTER_ID)
            await self._repo.save(game)

        return game

    # ---- валидация и применение хода (чистая логика, без I/O) ---------------

    def _validate_move(self, game: Game, user_id: UUID, new_board: Board) -> bool:
        symbol = game.symbol_for(user_id)
        changes = 0
        for i in range(3):
            for j in range(3):
                old_cell = game.board.get_cell(i, j)
                new_cell = new_board.get_cell(i, j)
                if old_cell != new_cell:
                    changes += 1
                    if not (old_cell == 0 and new_cell == symbol):
                        return False
        return changes == 1

    def _apply_move(self, game: Game, new_board: Board, mover_id: UUID) -> Game:
        """Возвращает новую Game с обновлённой доской и пересчитанным состоянием."""
        new_state: GameState
        winner_symbol = self._check_winner(new_board)
        if winner_symbol != 0:
            new_state = Win(mover_id)
        elif not new_board.has_empty_cells():
            new_state = Draw()
        else:
            opponent_id = game.opponent_of(mover_id)
            if opponent_id is None:
                # Невозможно: ходить может только участник игры, а ходы в игре без
                # соперника отсекаются раньше.
                raise ValueError("Move made in a game without an opponent")
            new_state = PlayerTurn(opponent_id)

        return Game(
            id=game.id,
            board=new_board,
            player_x_id=game.player_x_id,
            player_o_id=game.player_o_id,
            state=new_state,
            created_at=game.created_at,
        )

    # ---- Minimax для хода компьютера (компьютер всегда играет за O) ---------

    def _compute_best_move(self, board: Board) -> Board:
        best_score = float("-inf")
        best_move = None

        for i in range(3):
            for j in range(3):
                if board.get_cell(i, j) == 0:
                    candidate = self._copy_board(board)
                    candidate.grid[i][j] = O_SYMBOL
                    score = self._minimax(candidate, 0, is_maximizing=False)
                    if score > best_score:
                        best_score = score
                        best_move = (i, j)

        if best_move is None:
            return board

        res = self._copy_board(board)
        res.grid[best_move[0]][best_move[1]] = O_SYMBOL
        return res

    def _check_winner(self, board: Board) -> int:
        """Возвращает 1 (победа X), -1 (победа O) или 0 (нет победителя)."""
        lines = []
        for i in range(3):
            lines.append([board.get_cell(i, j) for j in range(3)])
            lines.append([board.get_cell(j, i) for j in range(3)])
        lines.append([board.get_cell(i, i) for i in range(3)])
        lines.append([board.get_cell(i, 2 - i) for i in range(3)])

        for line in lines:
            if line[0] != 0 and line[0] == line[1] == line[2]:
                return line[0]
        return 0

    def _minimax(self, board: Board, depth: int, is_maximizing: bool) -> int:
        """
        :param board: текущая доска
        :param depth: глубина рекурсии (предпочтение быстрых побед)
        :param is_maximizing: True, если ход компьютера (максимизирующего игрока),
                              False, если ход человека (минимизирующего)
        :return: оценка позиции (с точки зрения компьютера)
        """
        return _minimax_cached(_flatten(board), depth, is_maximizing)

    def _copy_board(self, board: Board) -> Board:
        new_grid = [row[:] for row in board.grid]
        return Board(grid=new_grid)
