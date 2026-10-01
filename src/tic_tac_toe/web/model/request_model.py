from pydantic import BaseModel, Field, field_validator


class BoardRequest(BaseModel):
    grid: list[list[int]] = Field(
        ...,
        min_length=3,
        max_length=3,
        description="3x3 игровое поле: 0 - пусто, 1 - X, -1 - O"
    )

    @field_validator('grid')
    def check_grid_dimensions(cls, v):
        if len(v) != 3:
            raise ValueError('grid must have exactly 3 rows')
        for row in v:
            if len(row) != 3:
                raise ValueError('each row must have exactly 3 columns')
            for cell in row:
                if cell not in (-1, 0, 1):
                    raise ValueError('cell value must be -1, 0, or 1')
        return v


class CreateGameRequest(BaseModel):
    vs_computer: bool = Field(
        default=False,
        description="true — соперник компьютер (можно ходить сразу); false — ждём второго игрока"
    )


class MoveRequest(BaseModel):
    board: BoardRequest


class SignUpRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=6, max_length=255)


class JwtRequest(BaseModel):
    login: str
    password: str

class RefreshJwtRequest(BaseModel):
    refreshToken: str
