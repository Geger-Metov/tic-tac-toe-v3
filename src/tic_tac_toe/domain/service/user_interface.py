from abc import ABC, abstractmethod
from uuid import UUID

from tic_tac_toe.domain.model.user import User


class IUserService(ABC):
    @abstractmethod
    async def register(self, login: str, password: str) -> User:
        """Создаёт пользователя. Кидает UserAlreadyExistsError, если login занят."""

    @abstractmethod
    async def get_by_login(self, login: str) -> User | None:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID) -> User | None:
        pass

    @abstractmethod
    async def verify_password(self, user: User | None, password: str) -> bool:
        """Проверка хэша (БД не трогает, но считается в отдельном потоке).
        user=None — логина нет: проверка всё равно выполняется (против
        хеша-пустышки) и возвращает False, чтобы не выдавать существование логина
        по времени ответа."""
