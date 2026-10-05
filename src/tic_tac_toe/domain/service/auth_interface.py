from abc import ABC, abstractmethod
from typing import Tuple
from uuid import UUID

from tic_tac_toe.domain.model.user import User


class IAuthService(ABC):
    """
    Возвращает пары (accessToken, refreshToken) как обычный tuple[str, str],
    а не web-модель JwtResponse — domain-слой не должен знать про Pydantic/
    HTTP (та же логика, что и раньше: web/mapper оборачивает результат в
    JwtResponse, а не наоборот).
    """

    @abstractmethod
    async def register(self, login: str, password: str) -> User:
        """Кидает UserAlreadyExistsError при дубле логина."""
        pass

    @abstractmethod
    async def authenticate(self, login: str, password: str) -> Tuple[str, str]:
        """Кидает InvalidCredentialsError при неверном логине/пароле и
        TooManyLoginAttemptsError, если для этого логина исчерпан лимит попыток."""
        pass

    @abstractmethod
    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        Кидает InvalidTokenError, если refreshToken битый/просрочен/не того
        типа/уже был использован. При успехе refreshToken считается
        использованным (single-use — см. общее описание задания), поэтому
        возвращается НОВАЯ пара токенов, а не только новый accessToken.
        """
        pass

    @abstractmethod
    async def refresh_refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        """
        См. refresh_access_token — по определению single-use refreshToken
        из общего описания задания оба метода обязаны консьюмить входной
        refreshToken и выдавать новую пару целиком, поэтому реализация
        идентична; два отдельных метода — по букве ТЗ (2 отдельных пункта
        и 2 отдельных эндпоинта), не потому что поведение должно различаться.
        """
        pass

    @abstractmethod
    async def get_user_id_from_access_token(self, access_token: str) -> UUID:
        """Кидает InvalidTokenError, если accessToken битый/просрочен/не того типа."""
        pass
