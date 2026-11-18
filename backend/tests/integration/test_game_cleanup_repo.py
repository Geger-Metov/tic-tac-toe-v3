from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.domain.model.board import Board
from tic_tac_toe.domain.model.game import Game
from tic_tac_toe.domain.model.game_state import PlayerTurn, WaitingForPlayer, Win
from tic_tac_toe.infrastructure.persistence.model.game_model import GameModel


def _game(state, age, player_o=None):
    x = uuid4()
    return Game(
        id=uuid4(),
        board=Board.create_empty(),
        player_x_id=x,
        player_o_id=player_o,
        state=state,
        created_at=datetime.now(UTC) - age,
    )


async def _existing(session, games):
    ids = [g.id for g in games]
    result = await session.execute(select(GameModel.id).where(GameModel.id.in_(ids)))
    return set(result.scalars().all())


async def test_deletes_only_old_games_that_wait_for_a_player(db_session):
    """Реальный SQL. Откат фикстуры вернёт всё на место, в том числе чужие
    старые игры в ожидании, если они есть в dev-БД и тоже попали под удаление."""
    repo = GameRepo(db_session)
    old_waiting = _game(WaitingForPlayer(), timedelta(days=2))
    fresh_waiting = _game(WaitingForPlayer(), timedelta(minutes=5))
    opponent = uuid4()
    old_in_progress = _game(PlayerTurn(uuid4()), timedelta(days=2), player_o=opponent)
    old_finished = _game(Win(uuid4()), timedelta(days=2), player_o=opponent)
    games = [old_waiting, fresh_waiting, old_in_progress, old_finished]
    for game in games:
        await repo.save(game)

    deleted = await repo.delete_abandoned_waiting(datetime.now(UTC) - timedelta(hours=24))

    assert deleted >= 1
    assert await _existing(db_session, games) == {
        fresh_waiting.id,
        old_in_progress.id,
        old_finished.id,
    }


async def test_cutoff_is_exclusive_of_newer_games(db_session):
    repo = GameRepo(db_session)
    waiting = _game(WaitingForPlayer(), timedelta(hours=2))
    await repo.save(waiting)

    await repo.delete_abandoned_waiting(datetime.now(UTC) - timedelta(hours=3))
    assert await _existing(db_session, [waiting]) == {waiting.id}  # моложе порога — на месте

    await repo.delete_abandoned_waiting(datetime.now(UTC) - timedelta(hours=1))
    assert await _existing(db_session, [waiting]) == set()  # старше порога — удалена
