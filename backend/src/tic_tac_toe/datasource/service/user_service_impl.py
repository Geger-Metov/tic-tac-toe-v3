import asyncio
from uuid import UUID, uuid4

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy.exc import IntegrityError

from tic_tac_toe.datasource.repository.user_repository import UserRepo
from tic_tac_toe.domain.exception.auth_exceptions import UserAlreadyExistsError
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.user_interface import IUserService

# argon2id (через pwdlib) с параметрами из минимальной рекомендации OWASP
# (19 МиБ памяти, 2 прохода, 1 поток). Значения по умолчанию
# (PasswordHash.recommended(): 64 МиБ, 4 потока) тяжелее: при параллельных
# входах контейнер быстро упирается в память.
# У argon2 нет лимита в 72 байта, как у bcrypt.
_hasher = PasswordHash((Argon2Hasher(time_cost=2, memory_cost=19456, parallelism=1),))

# Хеш-«пустышка»: когда логина нет в БД, пароль всё равно проверяется против
# него, чтобы время ответа не выдавало, существует ли пользователь.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-equalization")


class UserService(IUserService):
    def __init__(self, repo: UserRepo) -> None:
        self._repo = repo

    async def register(self, login: str, password: str) -> User:
        existing = await self._repo.find_by_login(login)
        if existing is not None:
            raise UserAlreadyExistsError(login)

        # Хеширование тяжёлое и синхронное — уводим из event loop в поток.
        password_hash = await asyncio.to_thread(_hasher.hash, password)

        user = User(id=uuid4(), login=login, password_hash=password_hash)
        try:
            await self._repo.save(user)
        except IntegrityError as e:
            # Гонка: параллельная регистрация того же логина прошла проверку
            # выше; уникальный индекс в БД её отсекает.
            raise UserAlreadyExistsError(login) from e
        return user

    async def get_by_login(self, login: str) -> User | None:
        return await self._repo.find_by_login(login)

    async def get_by_id(self, id: UUID) -> User | None:
        return await self._repo.find_by_id(id)

    async def verify_password(self, user: User | None, password: str) -> bool:
        """user=None (логина нет) проверяется против хеша-пустышки и всегда
        даёт False — так время ответа не зависит от существования логина."""
        hash_to_check = user.password_hash if user is not None else _DUMMY_HASH
        try:
            # У pwdlib порядок аргументов: сначала пароль, потом хеш.
            ok = await asyncio.to_thread(_hasher.verify, password, hash_to_check)
        except UnknownHashError:
            return False
        return ok and user is not None
