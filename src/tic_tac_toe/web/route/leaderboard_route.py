from typing import List

from fastapi import APIRouter, Depends, Query

from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.web.mapper.domain_web_mapper import GameWebMapper
from tic_tac_toe.web.model.response_model import LeaderboardEntryResponse
from tic_tac_toe.web.route.game_route import get_game_service
from tic_tac_toe.web.security.user_authenticator import get_current_user_id


router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get("", response_model=List[LeaderboardEntryResponse])
async def get_leaderboard(
    # Верхняя граница защищает от запроса "дай мне всех" одним вызовом.
    n: int = Query(default=10, ge=1, le=100, description="Сколько лучших игроков вернуть"),
    service: IGameService = Depends(get_game_service),
):
    """Топ-N игроков по доле побед среди завершённых игр (лучшие первыми)."""
    ratings = await service.get_top_players(n)
    return [GameWebMapper.rating_to_response(r) for r in ratings]
