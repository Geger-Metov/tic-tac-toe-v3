from typing import Optional

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.datasource.repository.refresh_token_store import RefreshTokenStore
from tic_tac_toe.datasource.repository.user_repository import UserRepo
from tic_tac_toe.datasource.service.auth_service_impl import AuthService
from tic_tac_toe.datasource.service.game_service_impl import GameService
from tic_tac_toe.datasource.service.jwt_provider_impl import JwtProvider
from tic_tac_toe.datasource.service.login_rate_limiter import LoginRateLimiter
from tic_tac_toe.datasource.service.user_service_impl import UserService
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.domain.service.jwt_interface import IJwtProvider
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.cache.redis_client import create_redis_client
from tic_tac_toe.infrastructure.security.jwt_config import (
    get_access_token_expires,
    get_jwt_secret_key,
    get_refresh_token_expires,
)
from tic_tac_toe.infrastructure.security.login_limit_config import (
    get_login_max_attempts,
    get_login_window_seconds,
)


class Container:
    """
    DI-контейнер.

    repo/service, зависящие от Session БД, создаются заново на каждый запрос.
    Не зависящие от запроса объекты живут в контейнере один раз: JwtProvider
    (секрет и сроки из конфига) и клиент Redis (он же пул соединений —
    пересоздавать его на каждый запрос было бы расточительно).

    redis_client можно подменить снаружи (тесты передают in-memory фейк);
    если не передан — создаётся настоящий по REDIS_URL.
    """

    def __init__(self, redis_client: Optional[Redis] = None) -> None:
        self._redis: Redis = redis_client if redis_client is not None else create_redis_client()
        self._refresh_expires = get_refresh_token_expires()
        self._jwt_provider: IJwtProvider = JwtProvider(
            secret_key=get_jwt_secret_key(),
            access_expires=get_access_token_expires(),
            refresh_expires=self._refresh_expires,
        )

    async def close(self) -> None:
        """Освобождает соединения Redis при остановке приложения."""
        await self._redis.aclose()

    def get_game_service(self, session: AsyncSession) -> IGameService:
        return GameService(GameRepo(session))

    def get_user_service(self, session: AsyncSession) -> IUserService:
        return UserService(UserRepo(session))

    def get_auth_service(self, session: AsyncSession) -> IAuthService:
        return AuthService(
            user_service=self.get_user_service(session),
            jwt_provider=self._jwt_provider,
            refresh_tokens=RefreshTokenStore(self._redis),
            login_limiter=LoginRateLimiter(
                self._redis,
                max_attempts=get_login_max_attempts(),
                window_seconds=get_login_window_seconds(),
            ),
            refresh_expires=self._refresh_expires,
        )
