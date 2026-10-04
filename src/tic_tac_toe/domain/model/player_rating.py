from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PlayerRating:
    """
    Строка лидерборда: игрок и его итоги по завершённым играм.

    Храним счётчики, а не готовый коэффициент: из них видно, откуда число
    взялось, а win_ratio считается в одном месте (ниже).
    """
    user_id: UUID
    login: str
    wins: int
    losses: int
    draws: int

    @property
    def games(self) -> int:
        return self.wins + self.losses + self.draws

    @property
    def win_ratio(self) -> float:
        """
        Доля побед среди завершённых игр: wins / (wins + losses + draws).
        
        Доля p = r / (1 + r) строго возрастает по r, поэтому ранжирует
        игроков в точности так же, как буквальное отношение r, но всегда
        конечна и лежит в [0, 1].

        ВАЖНО: ту же формулу повторяет ORDER BY в GameRepo.find_top_players —
        сортировку должна делать БД (иначе не выбрать top N одним запросом),
        так что при изменении формулы править нужно оба места.
        """
        if self.games == 0:
            return 0.0
        return self.wins / self.games
