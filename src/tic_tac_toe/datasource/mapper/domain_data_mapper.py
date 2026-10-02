from typing import Optional, Tuple
from uuid import UUID

from tic_tac_toe.domain.model.game import Game as DomainGame
from tic_tac_toe.domain.model.board import Board as DomainBoard
from tic_tac_toe.domain.model.game_state import Draw, GameState, PlayerTurn, WaitingForPlayer, Win
from tic_tac_toe.infrastructure.persistence.model.game_model import GameModel, GameStatus


def to_data(domain: DomainGame) -> GameModel:
    status, status_player_id = _state_to_columns(domain.state)
    return GameModel(
        id=domain.id,
        board=domain.board.grid,
        player_x_id=domain.player_x_id,
        player_o_id=domain.player_o_id,
        status=status,
        status_player_id=status_player_id,
        created_at=domain.created_at,
    )


def to_domain(data: GameModel) -> DomainGame:
    return DomainGame(
        id=data.id,
        board=DomainBoard(grid=data.board),
        player_x_id=data.player_x_id,
        player_o_id=data.player_o_id,
        state=_columns_to_state(data.status, data.status_player_id),
        created_at=data.created_at,
    )


def _state_to_columns(state: GameState) -> Tuple[GameStatus, Optional[UUID]]:
    if isinstance(state, WaitingForPlayer):
        return GameStatus.WAITING_FOR_PLAYER, None
    if isinstance(state, PlayerTurn):
        return GameStatus.PLAYER_TURN, state.player_id
    if isinstance(state, Draw):
        return GameStatus.DRAW, None
    if isinstance(state, Win):
        return GameStatus.WIN, state.player_id
    raise ValueError(f"Unknown game state: {state!r}")  # pragma: no cover


def _columns_to_state(status: GameStatus, status_player_id: Optional[UUID]) -> GameState:
    if status == GameStatus.WAITING_FOR_PLAYER:
        return WaitingForPlayer()
    if status == GameStatus.PLAYER_TURN:
        return PlayerTurn(status_player_id)
    if status == GameStatus.DRAW:
        return Draw()
    if status == GameStatus.WIN:
        return Win(status_player_id)
    raise ValueError(f"Unknown status: {status!r}")  # pragma: no cover
