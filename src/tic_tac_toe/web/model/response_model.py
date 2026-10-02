from pydantic import BaseModel
from uuid import UUID
from typing import Optional
from datetime import datetime


class BoardResponse(BaseModel):
    grid: list[list[int]]


class GameStateResponse(BaseModel):
    status: str  # "WAITING_FOR_PLAYER" | "PLAYER_TURN" | "DRAW" | "WIN"
    # Чей ход (PLAYER_TURN) или победитель (WIN); отсутствует для WAITING_FOR_PLAYER/DRAW.
    # Значение "00000000-0000-0000-0000-000000000000" означает компьютера
    # (см. domain.model.game.COMPUTER_ID) — для удобства клиента то же самое
    # говорит поле vs_computer ниже, на COMPUTER_ID можно не завязываться.
    player_id: Optional[UUID] = None


class GameResponse(BaseModel):
    id: UUID
    board: BoardResponse
    player_x_id: UUID
    player_o_id: Optional[UUID]
    vs_computer: bool
    state: GameStateResponse
    created_at: datetime


class SignUpResponse(BaseModel):
    success: bool
    id: UUID


class JwtResponse(BaseModel):
    type: str = "Bearer"
    accessToken: str
    refreshToken: str


class UserResponse(BaseModel):
    id: UUID
    login: str
