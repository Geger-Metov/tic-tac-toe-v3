from base64 import b64decode
from uuid import UUID
import binascii

from tic_tac_toe.domain.exception.auth_exceptions import InvalidCredentialsError
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.user_interface import IUserService


class AuthService(IAuthService):
    def __init__(self, user_service: IUserService) -> None:
        self._user_service = user_service

    async def register(self, login: str, password: str) -> User:
        # AuthService не хранит пользователей сам — это ответственность UserService,
        # AuthService лишь предоставляет фасад для веб-слоя (как и просит ТЗ:
        # "authorization service that uses UserService").
        return await self._user_service.register(login, password)

    async def authenticate(self, authorization_header: str) -> UUID:
        login, password = self._decode_basic_auth(authorization_header)

        user = await self._user_service.get_by_login(login)
        if user is None or not self._user_service.verify_password(user, password):
            raise InvalidCredentialsError()

        return user.id

    @staticmethod
    def _decode_basic_auth(header_value: str) -> tuple[str, str]:
        """Разбирает 'Basic base64(login:password)' по RFC 7617."""
        scheme, _, encoded = header_value.partition(" ")
        if scheme.lower() != "basic" or not encoded:
            raise InvalidCredentialsError()

        try:
            decoded = b64decode(encoded, validate=True).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            raise InvalidCredentialsError()

        login, separator, password = decoded.partition(":")
        if not separator:
            raise InvalidCredentialsError()

        return login, password
