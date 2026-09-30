from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from tic_tac_toe.domain.model.user import User


class IUserService(ABC):
    @abstractmethod
    async def register(self, login: str, password: str) -> User:
        """Создаёт пользователя. Кидает UserAlreadyExistsError, если login занят."""
        pass

    @abstractmethod
    async def get_by_login(self, login: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    def verify_password(self, user: User, password: str) -> bool:
        """Чистая проверка хэша, БД не трогает — остаётся синхронной."""
        pass
