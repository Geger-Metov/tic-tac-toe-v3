from uuid import uuid4

import pytest

from tic_tac_toe.datasource.service.game_service_impl import GameService
from tic_tac_toe.domain.exception.game_exceptions import (
    GameNotFoundError,
    GameNotJoinableError,
    InvalidMoveError,
    InvalidTurnError,
    NotParticipantError,
)
from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game import COMPUTER_ID
from tic_tac_toe.domain.model.game_state import Draw, PlayerTurn, WaitingForPlayer, Win
from tic_tac_toe.domain.model.player_rating import PlayerRating


class FakeGameRepo:
    """In-memory замена GameRepo — GameService от него зависит только по
    интерфейсу (save/find_by_id/find_waiting_games), реальная БД тут не нужна:
    это тест бизнес-логики, а не персистентности."""

    def __init__(self) -> None:
        self.store = {}
        self.ratings = []  # то, что "вернёт БД" на find_top_players
        self.last_top_n = None

    async def save(self, game) -> None:
        self.store[game.id] = game

    async def find_by_id(self, uid):
        return self.store.get(uid)

    async def find_waiting_games(self):
        return [g for g in self.store.values() if isinstance(g.state, WaitingForPlayer)]

    async def find_top_players(self, n):
        self.last_top_n = n
        return self.ratings[:n]

    async def find_finished_by_user(self, user_id):
        finished = [
            g for g in self.store.values()
            if isinstance(g.state, (Win, Draw)) and user_id in (g.player_x_id, g.player_o_id)
        ]
        return sorted(finished, key=lambda g: g.created_at, reverse=True)


@pytest.fixture
def service() -> GameService:
    return GameService(FakeGameRepo())


async def test_create_game_vs_human_starts_waiting(service):
    alice = uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)

    assert isinstance(game.state, WaitingForPlayer)
    assert game.player_x_id == alice
    assert game.player_o_id is None


async def test_create_game_vs_computer_starts_immediately(service):
    alice = uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=True)

    assert isinstance(game.state, PlayerTurn)
    assert game.state.player_id == alice
    assert game.player_o_id == COMPUTER_ID
    assert game.is_vs_computer is True


async def test_available_games_lists_only_waiting(service):
    alice, bob = uuid4(), uuid4()
    waiting = await service.create_game(creator_id=alice, vs_computer=False)
    await service.create_game(creator_id=bob, vs_computer=True)  # не должна попасть в список

    available = await service.get_available_games()

    assert [g.id for g in available] == [waiting.id]


async def test_cannot_join_own_game(service):
    alice = uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)

    with pytest.raises(GameNotJoinableError):
        await service.join_game(game.id, alice)


async def test_join_sets_turn_to_creator(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)

    joined = await service.join_game(game.id, bob)

    assert joined.player_o_id == bob
    assert isinstance(joined.state, PlayerTurn)
    assert joined.state.player_id == alice  # X (создатель) всегда первый


async def test_joined_game_disappears_from_available(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    assert await service.get_available_games() == []


async def test_move_out_of_turn_rejected(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    board = Board(grid=[[-1, 0, 0], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(InvalidTurnError):
        await service.make_move(game.id, bob, board)


async def test_move_by_non_participant_rejected(service):
    alice, bob, mallory = uuid4(), uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    board = Board(grid=[[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(NotParticipantError):
        await service.make_move(game.id, mallory, board)


async def test_move_with_two_changed_cells_rejected(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    board = Board(grid=[[1, 1, 0], [0, 0, 0], [0, 0, 0]])
    with pytest.raises(InvalidMoveError):
        await service.make_move(game.id, alice, board)


async def test_move_with_wrong_symbol_rejected(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    board = Board(grid=[[-1, 0, 0], [0, 0, 0], [0, 0, 0]])  # alice — X, а ставит O
    with pytest.raises(InvalidMoveError):
        await service.make_move(game.id, alice, board)


async def test_valid_move_passes_turn_to_opponent(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    board = Board(grid=[[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    updated = await service.make_move(game.id, alice, board)

    assert isinstance(updated.state, PlayerTurn)
    assert updated.state.player_id == bob


async def test_win_is_detected_and_ends_game(service):
    alice, bob = uuid4(), uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=False)
    await service.join_game(game.id, bob)

    # X: (0,0),(0,1),(0,2) — победа по верхней строке; O ходит куда угодно между
    await service.make_move(game.id, alice, Board(grid=[[1, 0, 0], [0, 0, 0], [0, 0, 0]]))
    await service.make_move(game.id, bob, Board(grid=[[1, 0, 0], [0, -1, 0], [0, 0, 0]]))
    await service.make_move(game.id, alice, Board(grid=[[1, 1, 0], [0, -1, 0], [0, 0, 0]]))
    await service.make_move(game.id, bob, Board(grid=[[1, 1, 0], [0, -1, 0], [0, 0, -1]]))
    final = await service.make_move(game.id, alice, Board(grid=[[1, 1, 1], [0, -1, 0], [0, 0, -1]]))

    assert isinstance(final.state, Win)
    assert final.state.player_id == alice

    # ход после победы запрещён
    with pytest.raises(InvalidTurnError):
        await service.make_move(game.id, bob, final.board)


async def test_computer_responds_within_same_call(service):
    alice = uuid4()
    game = await service.create_game(creator_id=alice, vs_computer=True)

    board = Board(grid=[[0, 0, 0], [0, 1, 0], [0, 0, 0]])
    updated = await service.make_move(game.id, alice, board)

    o_count = sum(row.count(-1) for row in updated.board.grid)
    assert o_count == 1
    assert isinstance(updated.state, PlayerTurn)
    assert updated.state.player_id == alice


async def test_unknown_game_raises_not_found(service):
    with pytest.raises(GameNotFoundError):
        await service.get_game_by_id(uuid4())


# ---- история игр -----------------------------------------------------------

X_WINS = [(0, 0), (1, 0), (0, 1), (1, 1), (0, 2)]  # X берёт верхнюю строку
DRAW = [(0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0), (2, 2)]


async def play_moves(service, game, moves):
    """Играет ходы по очереди (X первым) за двух людей, возвращает итоговую игру."""
    grid = [[0] * 3 for _ in range(3)]
    players = [(game.player_x_id, 1), (game.player_o_id, -1)]
    result = game
    for i, (row, col) in enumerate(moves):
        player_id, symbol = players[i % 2]
        grid[row][col] = symbol
        result = await service.make_move(
            game.id, player_id, Board(grid=[r[:] for r in grid])
        )
    return result


async def new_human_game(service, x, o):
    game = await service.create_game(creator_id=x, vs_computer=False)
    return await service.join_game(game.id, o)


async def test_created_at_is_set_and_preserved(service):
    alice, bob = uuid4(), uuid4()
    created = await service.create_game(creator_id=alice, vs_computer=False)
    joined = await service.join_game(created.id, bob)
    after_move = await service.make_move(
        created.id, alice, Board(grid=[[1, 0, 0], [0, 0, 0], [0, 0, 0]])
    )

    assert created.created_at is not None
    assert created.created_at.tzinfo is not None  # UTC, не "наивное" время
    assert joined.created_at == created.created_at
    assert after_move.created_at == created.created_at


async def test_finished_games_include_win_and_draw_for_both_players(service):
    alice, bob = uuid4(), uuid4()
    won = await play_moves(service, await new_human_game(service, alice, bob), X_WINS)
    drawn = await play_moves(service, await new_human_game(service, alice, bob), DRAW)
    assert isinstance(won.state, Win)
    assert isinstance(drawn.state, Draw)

    for user in (alice, bob):
        history = await service.get_finished_games_by_user(user)
        assert {g.id for g in history} == {won.id, drawn.id}


async def test_finished_games_exclude_unfinished_and_foreign(service):
    alice, bob, carol, dave = uuid4(), uuid4(), uuid4(), uuid4()
    finished = await play_moves(service, await new_human_game(service, alice, bob), X_WINS)
    await new_human_game(service, alice, carol)                     # идёт, ходов нет
    await service.create_game(creator_id=alice, vs_computer=False)  # ждёт соперника
    await service.create_game(creator_id=alice, vs_computer=True)   # идёт против компьютера
    await play_moves(service, await new_human_game(service, carol, dave), X_WINS)  # чужая

    history = await service.get_finished_games_by_user(alice)

    assert [g.id for g in history] == [finished.id]
    assert await service.get_finished_games_by_user(uuid4()) == []


async def test_finished_games_newest_first(service):
    alice, bob = uuid4(), uuid4()
    first = await play_moves(service, await new_human_game(service, alice, bob), X_WINS)
    second = await play_moves(service, await new_human_game(service, alice, bob), X_WINS)

    history = await service.get_finished_games_by_user(alice)

    assert [g.id for g in history] == [second.id, first.id]


# ---- лидерборд -------------------------------------------------------------
# Сам SQL-запрос здесь не проверяется (фейковый репозиторий) — это делают
# интеграционные тесты. Тут: расчёт коэффициента и поведение сервиса.

def rating(wins, losses, draws, login="p"):
    return PlayerRating(user_id=uuid4(), login=login, wins=wins, losses=losses, draws=draws)


def test_win_ratio_is_share_of_finished_games():
    assert rating(2, 1, 0).win_ratio == 2 / 3
    assert rating(1, 1, 2).win_ratio == 0.25
    assert rating(3, 0, 0).win_ratio == 1.0
    assert rating(0, 2, 1).win_ratio == 0.0


def test_win_ratio_without_games_is_zero():
    assert rating(0, 0, 0).games == 0
    assert rating(0, 0, 0).win_ratio == 0.0


def test_win_ratio_ranks_like_wins_to_losses_and_draws():
    """Доля побед упорядочивает игроков так же, как буквальное отношение из ТЗ
    wins / (losses + draws), но определена и для непобеждённых игроков."""
    players = [rating(5, 0, 0), rating(4, 1, 0), rating(2, 1, 1), rating(1, 3, 0), rating(0, 1, 0)]

    by_share = sorted(players, key=lambda p: -p.win_ratio)
    by_literal = sorted(
        players,
        key=lambda p: -(p.wins / (p.losses + p.draws) if p.losses + p.draws else float("inf")),
    )

    assert by_share == by_literal


async def test_top_players_passes_n_to_repo(service):
    top = [rating(3, 0, 0, "a"), rating(1, 1, 0, "b")]
    service._repo.ratings = top

    assert await service.get_top_players(2) == top
    assert service._repo.last_top_n == 2
    assert await service.get_top_players(1) == top[:1]


async def test_top_players_with_non_positive_n_is_empty_and_skips_repo(service):
    service._repo.ratings = [rating(3, 0, 0)]

    assert await service.get_top_players(0) == []
    assert await service.get_top_players(-5) == []
    assert service._repo.last_top_n is None
