from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.datasource.repository.game_repository import GameRepo
from tic_tac_toe.datasource.repository.user_repository import UserRepo
from tic_tac_toe.datasource.service.auth_service_impl import AuthService
from tic_tac_toe.datasource.service.game_service_impl import GameService
from tic_tac_toe.datasource.service.user_service_impl import UserService
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.domain.service.user_interface import IUserService


class Container:
    """
    DI-контейнер.

    Данные хранятся в PostgreSQL, доступ к которой даёт SQLAlchemy AsyncSession.
    Session привязана к жизненному циклу одного HTTP-запроса (см.
    infrastructure.database.session.get_db_session), поэтому repo/service здесь
    принципиально НЕ синглтоны — они создаются заново на каждый запрос, с той
    самой request-scoped session.
    """

    def get_game_service(self, session: AsyncSession) -> IGameService:
        repo = GameRepo(session)
        return GameService(repo)

    def get_user_service(self, session: AsyncSession) -> IUserService:
        repo = UserRepo(session)
        return UserService(repo)

    def get_auth_service(self, session: AsyncSession) -> IAuthService:
        # AuthService — фасад поверх UserService, своего repo не имеет
        user_service = self.get_user_service(session)
        return AuthService(user_service)
