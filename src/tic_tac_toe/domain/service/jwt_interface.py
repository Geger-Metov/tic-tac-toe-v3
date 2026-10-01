from abc import ABC, abstractmethod
from uuid import UUID

from tic_tac_toe.domain.model.user import User


class IJwtProvider(ABC):
    """
    Чистая обёртка над кодированием/декодированием JWT — аналог
    flask_jwt_extended из ТЗ, но без привязки к Flask (используем PyJWT
    напрямую). Не обращается к БД и не хранит состояние между вызовами —
    вся работа с "использован ли этот refreshToken" находится в AuthService,
    а не здесь (см. auth_service_impl.py).
    """

    @abstractmethod
    def generate_access_token(self, user: User) -> str:
        pass

    @abstractmethod
    def generate_refresh_token(self, user: User) -> str:
        pass

    @abstractmethod
    def validate_access_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def validate_refresh_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def get_user_id(self, token: str) -> UUID:
        """Кидает InvalidTokenError, если токен нечитаемый (используется и
        для access, и для refresh — тип токена уже должен быть проверен
        отдельно через validate_*_token)."""
        pass

    @abstractmethod
    def get_jti(self, token: str) -> str:
        """
        Уникальный идентификатор конкретного токена (claim "jti"). Не входит
        в список методов из ТЗ буквально, но необходим AuthService, чтобы
        отследить в БД, использован ли уже этот конкретный refreshToken —
        без этого "single-use" из общего описания задания нечем обеспечить
        на сервере (JWT сам по себе безсостоятелен).
        """
        pass
