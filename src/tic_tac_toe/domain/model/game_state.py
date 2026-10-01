from dataclasses import dataclass
from typing import Union
from uuid import UUID


@dataclass(frozen=True)
class WaitingForPlayer:
    """Игра создана, второй игрок ещё не присоединился (только для игр не с компьютером)."""
    pass


@dataclass(frozen=True)
class PlayerTurn:
    """Сейчас ход игрока с этим UUID (может быть COMPUTER_ID — см. domain.model.game)."""
    player_id: UUID


@dataclass(frozen=True)
class Draw:
    """Игра окончена вничью."""
    pass


@dataclass(frozen=True)
class Win:
    """Игра окончена победой игрока с этим UUID (может быть COMPUTER_ID)."""
    player_id: UUID


# Sum type: ровно одно из состояний ТЗ ("Waiting for players; Player's turn with
# UUID; Draw; Victory for player with UUID"), каждое несёт только те данные,
# которые ему реально нужны — вместо набора необязательных полей на самом Game
# (что позволило бы собрать бессмысленные комбинации вроде "DRAW, но с player_id").
GameState = Union[WaitingForPlayer, PlayerTurn, Draw, Win]
