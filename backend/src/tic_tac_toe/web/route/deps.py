from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.di.container import Container
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.database.session import get_db_session
from tic_tac_toe.web.security.user_authenticator import get_current_user_id

DbSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_game_service(request: Request, session: DbSession) -> IGameService:
    return get_container(request).get_game_service(session)


def get_auth_service(request: Request, session: DbSession) -> IAuthService:
    return get_container(request).get_auth_service(session)


def get_user_service(request: Request, session: DbSession) -> IUserService:
    return get_container(request).get_user_service(session)


GameServiceDep = Annotated[IGameService, Depends(get_game_service)]
AuthServiceDep = Annotated[IAuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[IUserService, Depends(get_user_service)]
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
