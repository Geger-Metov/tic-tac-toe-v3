from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from tic_tac_toe.domain.exception.game_exceptions import (
    GameNotFoundError,
    GameNotJoinableError,
    InvalidMoveError,
    InvalidTurnError,
    NotParticipantError,
)
from tic_tac_toe.web.mapper.domain_web_mapper import GameWebMapper
from tic_tac_toe.web.model.request_model import CreateGameRequest, MoveRequest
from tic_tac_toe.web.model.response_model import GameResponse
from tic_tac_toe.web.route.deps import CurrentUserId, GameServiceDep, get_current_user_id

router = APIRouter(
    prefix="/game",
    tags=["game"],
    dependencies=[Depends(get_current_user_id)],  # все эндпоинты игры — только для авторизованных
)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_game(
    request_data: CreateGameRequest,
    service: GameServiceDep,
    user_id: CurrentUserId,
) -> GameResponse:
    """Создаёт новую игру с человеком (ждёт второго игрока) или с компьютером."""
    game = await service.create_game(creator_id=user_id, vs_computer=request_data.vs_computer)
    return GameWebMapper.domain_to_response(game)


# Важно: этот маршрут должен быть объявлен РАНЬШЕ "/{game_id}" — иначе FastAPI
# попытается распарсить "available" как UUID для {game_id} и вернёт 422,
# так и не дойдя до этого обработчика.
@router.get("/available")
async def list_available_games(
    service: GameServiceDep,
    # UserAuthenticator: сам список не персонализирован, но эндпоинт всё равно
    # закрыт — по ТЗ авторизация обязательна для всех эндпоинтов, кроме
    # регистрации и логина.
) -> list[GameResponse]:
    """Игры, ожидающие второго игрока-человека (создатель ждёт присоединения)."""
    games = await service.get_available_games()
    return [GameWebMapper.domain_to_response(g) for g in games]


# Как и "/available", объявлен РАНЬШЕ "/{game_id}" — иначе "history" будет
# принят за UUID и запрос получит 422.
@router.get("/history")
async def list_finished_games(
    service: GameServiceDep,
    user_id: CurrentUserId,
) -> list[GameResponse]:
    """Завершённые игры (победа/ничья) текущего пользователя — определяется
    по accessToken, а не по параметру запроса: чужую историю так не получить."""
    games = await service.get_finished_games_by_user(user_id)
    return [GameWebMapper.domain_to_response(g) for g in games]


@router.get("/{game_id}")
async def get_game(
    game_id: UUID,
    service: GameServiceDep,
) -> GameResponse:
    try:
        game = await service.get_game_by_id(game_id)
    except GameNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return GameWebMapper.domain_to_response(game)


@router.post("/{game_id}/join")
async def join_game(
    game_id: UUID,
    service: GameServiceDep,
    user_id: CurrentUserId,
) -> GameResponse:
    try:
        game = await service.join_game(game_id, user_id)
    except GameNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    except GameNotJoinableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return GameWebMapper.domain_to_response(game)


@router.patch("/{game_id}")
async def make_move(
    game_id: UUID,
    request_data: MoveRequest,
    service: GameServiceDep,
    user_id: CurrentUserId,
) -> GameResponse:

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
