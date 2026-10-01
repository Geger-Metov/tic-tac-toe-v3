from fastapi import APIRouter, Depends, HTTPException, status,Request
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from tic_tac_toe.domain.exception.game_exceptions import (
    GameNotFoundError,
    GameNotJoinableError,
    InvalidMoveError,
    InvalidTurnError,
    NotParticipantError,
)
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.infrastructure.database.session import get_db_session
from tic_tac_toe.web.mapper.domain_web_mapper import GameWebMapper
from tic_tac_toe.web.model.request_model import CreateGameRequest, MoveRequest
from tic_tac_toe.web.model.response_model import GameResponse
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

router = APIRouter(prefix="/game", tags=["game"])


def get_game_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> IGameService:
    container = request.app.state.container
    return container.get_game_service(session)


@router.post("", response_model=GameResponse, status_code=status.HTTP_201_CREATED)
async def create_game(
    request_data: CreateGameRequest,
    service: IGameService = Depends(get_game_service),
    user_id: UUID = Depends(get_current_user_id),
):
    """Создаёт новую игру с человеком (ждёт второго игрока) или с компьютером."""
    game = await service.create_game(creator_id=user_id, vs_computer=request_data.vs_computer)
    return GameWebMapper.domain_to_response(game)


# Важно: этот маршрут должен быть объявлен РАНЬШЕ "/{game_id}" — иначе FastAPI
# попытается распарсить "available" как UUID для {game_id} и вернёт 422,
# так и не дойдя до этого обработчика.
@router.get("/available", response_model=list[GameResponse])
async def list_available_games(
    service: IGameService = Depends(get_game_service),
):
    """Игры, ожидающие второго игрока-человека (создатель ждёт присоединения)."""
    games = await service.get_available_games()
    return [GameWebMapper.domain_to_response(g) for g in games]


@router.get("/{game_id}", response_model=GameResponse)
async def get_game(
    game_id: UUID,
    service: IGameService = Depends(get_game_service),
):
    try:
        game = await service.get_game_by_id(game_id)
    except GameNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return GameWebMapper.domain_to_response(game)


@router.post("/{game_id}/join", response_model=GameResponse)
async def join_game(
    game_id: UUID,
    service: IGameService = Depends(get_game_service),
    user_id: UUID = Depends(get_current_user_id),
):
    try:
        game = await service.join_game(game_id, user_id)
    except GameNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    except GameNotJoinableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return GameWebMapper.domain_to_response(game)


@router.patch("/{game_id}", response_model=GameResponse)
async def make_move(
    game_id: UUID,
    request_data: MoveRequest,
    service: IGameService = Depends(get_game_service),
    user_id: UUID = Depends(get_current_user_id),
):

    new_board = GameWebMapper.board_request_to_domain(request_data.board)

    try:
        game = await service.make_move(game_id, user_id, new_board)
    except GameNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    except NotParticipantError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a participant of this game",
        )
    except InvalidTurnError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="It's not your turn, the game hasn't started, or it's already finished",
        )
    except InvalidMoveError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid move: change exactly one empty cell to your own symbol",
        )
    return GameWebMapper.domain_to_response(game)
