from abc import ABC, abstractmethod
from uuid import UUID

from tic_tac_toe.domain.model.user import User


class IAuthService(ABC):
    @abstractmethod
    async def register(self, login: str, password: str) -> User:
        """Регистрация поверх UserService. Кидает UserAlreadyExistsError при дубле логина."""
        pass

    @abstractmethod
    async def authenticate(self, authorization_header: str) -> UUID:
        """
        Принимает сырое значение заголовка Authorization
        (ожидается "Basic base64(login:password)", см. RFC 7617),
        возвращает UUID пользователя при успехе.
        Кидает InvalidCredentialsError, если заголовок битый, логина
        не существует или пароль не совпал.
        """
        pass
