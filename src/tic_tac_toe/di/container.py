from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.datasource.repository.refresh_token_repository import RefreshTokenRepo
from tic_tac_toe.datasource.repository.user_repository import UserRepo
from tic_tac_toe.datasource.service.auth_service_impl import AuthService
from tic_tac_toe.datasource.service.game_service_impl import GameService
from tic_tac_toe.datasource.service.jwt_provider_impl import JwtProvider
from tic_tac_toe.datasource.service.user_service_impl import UserService
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.domain.service.jwt_interface import IJwtProvider
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.security.jwt_config import (
    get_access_token_expires,
    get_jwt_secret_key,
    get_refresh_token_expires,
)

class Container:
    """
    DI-контейнер.

    repo/service, зависящие от Session, создаются заново на каждый запрос.
    JwtProvider, наоборот, не зависит от запроса (только от секрета и сроков
    жизни из конфига), поэтому он единственный живёт как синглтон в контейнере.
    """

    def __init__(self) -> None:
        self._refresh_expires = get_refresh_token_expires()
        self._jwt_provider: IJwtProvider = JwtProvider(
            secret_key=get_jwt_secret_key(),
            access_expires=get_access_token_expires(),
            refresh_expires=self._refresh_expires,
        )

    def get_game_service(self, session: AsyncSession) -> IGameService:
        return GameService(GameRepo(session))

    def get_user_service(self, session: AsyncSession) -> IUserService:
        return UserService(UserRepo(session))

    def get_auth_service(self, session: AsyncSession) -> IAuthService:
        return AuthService(
            user_service=self.get_user_service(session),
            jwt_provider=self._jwt_provider,
            refresh_token_repo=RefreshTokenRepo(session),
            refresh_expires=self._refresh_expires,
        )
