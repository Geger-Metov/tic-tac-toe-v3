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
from tic_tac_toe.domain.model.game_state import PlayerTurn, WaitingForPlayer, Win


class FakeGameRepo:
    """In-memory замена GameRepo — GameService от него зависит только по
    интерфейсу (save/find_by_id/find_waiting_games), реальная БД тут не нужна:
    это тест бизнес-логики, а не персистентности."""

    def __init__(self) -> None:
        self.store = {}

    async def save(self, game) -> None:
        self.store[game.id] = game

    async def find_by_id(self, uid):
        return self.store.get(uid)

    async def find_waiting_games(self):
        return [g for g in self.store.values() if isinstance(g.state, WaitingForPlayer)]


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
