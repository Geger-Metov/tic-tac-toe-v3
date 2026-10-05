from datetime import timedelta
from typing import Tuple
from uuid import UUID

from tic_tac_toe.datasource.repository.refresh_token_store import RefreshTokenStore
from tic_tac_toe.datasource.service.login_rate_limiter import LoginRateLimiter
from tic_tac_toe.domain.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from tic_tac_toe.domain.model.user import User
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.jwt_interface import IJwtProvider
from tic_tac_toe.domain.service.user_interface import IUserService


class AuthService(IAuthService):
    def __init__(
        self,
        user_service: IUserService,
        jwt_provider: IJwtProvider,
        refresh_tokens: RefreshTokenStore,
        login_limiter: LoginRateLimiter,
        refresh_expires: timedelta,
    ) -> None:
        self._user_service = user_service
        self._jwt_provider = jwt_provider
        self._refresh_tokens = refresh_tokens
        self._login_limiter = login_limiter
        self._refresh_expires = refresh_expires

    async def register(self, login: str, password: str) -> User:
        return await self._user_service.register(login, password)

    async def authenticate(self, login: str, password: str) -> Tuple[str, str]:
        # Попытка засчитывается СРАЗУ и атомарно, до проверки пароля — иначе
        # параллельные запросы обходят лимит (подробности в LoginRateLimiter).
        # У заблокированного логина пароль не проверяется вообще (bcrypt зря
        # не считается). Считаются и несуществующие логины.
        await self._login_limiter.begin_attempt(login)

        user = await self._user_service.get_by_login(login)
        if user is None or not self._user_service.verify_password(user, password):
            # Попытка уже засчитана — отдельно "записывать неудачу" не нужно.
            raise InvalidCredentialsError()

        await self._login_limiter.reset(login)
        return await self._issue_token_pair(user)

    async def refresh_access_token(self, refresh_token: str) -> Tuple[str, str]:
        return await self._rotate(refresh_token)

    async def refresh_refresh_token(self, refresh_token: str) -> Tuple[str, str]:
        return await self._rotate(refresh_token)

    async def get_user_id_from_access_token(self, access_token: str) -> UUID:
        if not self._jwt_provider.validate_access_token(access_token):
            raise InvalidTokenError("invalid access token")
        return self._jwt_provider.get_user_id(access_token)

    # ---- внутреннее ----------------------------------------------------

    async def _rotate(self, refresh_token: str) -> Tuple[str, str]:
        """
        Проверяет подпись/срок/тип, затем атомарно "захватывает" токен в Redis
        (RefreshTokenStore.claim = GETDEL) и выдаёт новую пару. Все причины
        отказа — битая подпись, истёк, не тот тип, неизвестный, уже
        использованный, проигранная гонка — сводятся к одному InvalidTokenError.
        """
        if not self._jwt_provider.validate_refresh_token(refresh_token):
            raise InvalidTokenError("invalid refresh token")

        try:
            jti = UUID(self._jwt_provider.get_jti(refresh_token))
        except ValueError:
            raise InvalidTokenError("invalid refresh token")

        user_id = await self._refresh_tokens.claim(jti)
        if user_id is None:
            raise InvalidTokenError("invalid refresh token")

        user = await self._user_service.get_by_id(user_id)
        if user is None:
            raise InvalidTokenError("invalid refresh token")

        return await self._issue_token_pair(user)

    async def _issue_token_pair(self, user: User) -> Tuple[str, str]:
        access_token = self._jwt_provider.generate_access_token(user)
        refresh_token = self._jwt_provider.generate_refresh_token(user)

        jti = UUID(self._jwt_provider.get_jti(refresh_token))
        await self._refresh_tokens.register(jti, user.id, self._refresh_expires)
        return access_token, refresh_token
