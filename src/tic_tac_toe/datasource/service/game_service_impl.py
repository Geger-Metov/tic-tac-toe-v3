from uuid import UUID

from tic_tac_toe.domain.exception.game_exceptions import (
    GameNotFoundError,
    GameNotJoinableError,
    InvalidMoveError,
    InvalidTurnError,
    NotParticipantError,
)
from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game import COMPUTER_ID, Game, O_SYMBOL, X_SYMBOL
from tic_tac_toe.domain.model.game_state import Draw, PlayerTurn, Win
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.datasource.repository.game_repository import GameRepo


class GameService(IGameService):
    WIN_SCORE = 10
    DRAW_SCORE = 0

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

    async def join_game(self, game_id: UUID, user_id: UUID) -> Game:
        game = await self.get_game_by_id(game_id)

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
            created_at=game.created_at
        )
        await self._repo.save(joined_game)
        return joined_game

    async def make_move(self, game_id: UUID, user_id: UUID, new_board: Board) -> Game:
        game = await self.get_game_by_id(game_id)

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
        winner_symbol = self._check_winner(new_board)
        if winner_symbol != 0:
            new_state = Win(mover_id)
        elif not new_board.has_empty_cells():
            new_state = Draw()
        else:
            opponent_id = game.opponent_of(mover_id)
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
        best_score = float('-inf')
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
        :param depth: глубина рекурсии (необязательно, но полезно для предпочтения быстрых побед)
        :param is_maximizing: True, если ход компьютера (максимизирующего игрока),
                              False, если ход человека (минимизирующего)
        :return: оценка позиции (с точки зрения компьютера)
        """
        winner = self._check_winner(board)
        if winner == O_SYMBOL:
            return self.WIN_SCORE - depth
        elif winner == X_SYMBOL:
            return -self.WIN_SCORE + depth
        elif not board.has_empty_cells():
            return self.DRAW_SCORE

        if is_maximizing:
            best = float('-inf')
            for i in range(3):
                for j in range(3):
                    if board.get_cell(i, j) == 0:
                        candidate = self._copy_board(board)
                        candidate.grid[i][j] = O_SYMBOL
                        score = self._minimax(candidate, depth + 1, False)
                        best = max(best, score)
            return int(best)
        else:
            best = float('inf')
            for i in range(3):
                for j in range(3):
                    if board.get_cell(i, j) == 0:
                        candidate = self._copy_board(board)
                        candidate.grid[i][j] = X_SYMBOL
                        score = self._minimax(candidate, depth + 1, True)
                        best = min(best, score)
            return int(best)

    def _copy_board(self, board: Board) -> Board:
        new_grid = [row[:] for row in board.grid]
        return Board(grid=new_grid)
