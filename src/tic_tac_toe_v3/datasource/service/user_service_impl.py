from uuid import UUID, uuid4
from typing import Optional
from bcrypt import hashpw, gensalt, checkpw

from tic_tac_toe.domain.exception.auth_exceptions import UserAlreadyExistsError
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.datasource.repository.user_repository import UserRepo


class UserService(IUserService):
    def __init__(self, repo: UserRepo) -> None:
        self._repo = repo

    async def register(self, login: str, password: str) -> User:
        existing = await self._repo.find_by_login(login)
        if existing is not None:
            raise UserAlreadyExistsError(login)

        password_hash = hashpw(
            password.encode("utf-8"), gensalt()
        ).decode("utf-8")

        user = User(id=uuid4(), login=login, password_hash=password_hash)
        await self._repo.save(user)
        return user

    async def get_by_login(self, login: str) -> Optional[User]:
        return await self._repo.find_by_login(login)

    async def get_by_id(self, id: UUID) -> Optional[User]:
        return await self._repo.find_by_id(id)

    def verify_password(self, user: User, password: str) -> bool:
        return checkpw(
            password.encode("utf-8"), user.password_hash.encode("utf-8")
        )
