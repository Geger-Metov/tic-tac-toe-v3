from fastapi import APIRouter, Depends, Query

from tic_tac_toe.web.mapper.domain_web_mapper import GameWebMapper
from tic_tac_toe.web.model.response_model import LeaderboardEntryResponse
from tic_tac_toe.web.route.deps import GameServiceDep
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

# Авторизация навешана на весь роутер (UserAuthenticator), а не на отдельные
# функции: рейтинг для всех одинаков, UUID запрашивающего эндпоинту не нужен,
# и если держать защиту только в виде неиспользуемого параметра функции, её
# легко потерять при правке — а так любой новый маршрут в этом роутере
# защищён автоматически.
router = APIRouter(
    prefix="/leaderboard",
    tags=["leaderboard"],
    dependencies=[Depends(get_current_user_id)],
)


@router.get("")
async def get_leaderboard(
    service: GameServiceDep,
    # Верхняя граница защищает от запроса "дай мне всех" одним вызовом.
    n: int = Query(default=10, ge=1, le=100, description="Сколько лучших игроков вернуть"),
) -> list[LeaderboardEntryResponse]:
    """Топ-N игроков по доле побед среди завершённых игр (лучшие первыми)."""
    ratings = await service.get_top_players(n)
    return [GameWebMapper.rating_to_response(r) for r in ratings]
