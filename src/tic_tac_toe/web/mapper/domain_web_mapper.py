from tic_tac_toe.domain.model.game import Game as DomainGame
from tic_tac_toe.domain.model.board import Board as DomainBoard
from tic_tac_toe.domain.model.game_state import Draw, PlayerTurn, WaitingForPlayer, Win
from tic_tac_toe.web.model.request_model import BoardRequest
from tic_tac_toe.web.model.response_model import GameResponse, BoardResponse, GameStateResponse


class GameWebMapper:
    @staticmethod
    def board_request_to_domain(request: BoardRequest) -> DomainBoard:
        return DomainBoard(grid=request.grid)

    @staticmethod
    def domain_to_response(domain: DomainGame) -> GameResponse:
        return GameResponse(
            id=domain.id,
            board=BoardResponse(grid=domain.board.grid),
            player_x_id=domain.player_x_id,
            player_o_id=domain.player_o_id,
            vs_computer=domain.is_vs_computer,
            state=GameWebMapper._state_to_response(domain),
        )

    @staticmethod
    def _state_to_response(domain: DomainGame) -> GameStateResponse:
        state = domain.state
        if isinstance(state, WaitingForPlayer):
            return GameStateResponse(status="WAITING_FOR_PLAYER")
        if isinstance(state, PlayerTurn):
            return GameStateResponse(status="PLAYER_TURN", player_id=state.player_id)
        if isinstance(state, Draw):
            return GameStateResponse(status="DRAW")
        if isinstance(state, Win):
            return GameStateResponse(status="WIN", player_id=state.player_id)
        raise ValueError(f"Unknown game state: {state!r}")  # pragma: no cover
