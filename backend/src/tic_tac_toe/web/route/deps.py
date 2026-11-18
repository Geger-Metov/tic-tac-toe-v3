from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.di.container import Container
from tic_tac_toe.domain.exception.auth_exceptions import InvalidTokenError
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.domain.service.game_interface import IGameService
from tic_tac_toe.domain.service.user_interface import IUserService
from tic_tac_toe.infrastructure.database.session import get_db_session

_BEARER_PREFIX = "Bearer "


DbSession = Annotated[AsyncSession, Depends(get_db_session, scope="function")]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_id(
    auth_service: AuthServiceDep,
    authorization: str | None = Header(default=None),
) -> UUID:
    """
    UserAuthenticator: Basic-авторизация убрана, вместо неё — Bearer.
    Достаёт accessToken из "Authorization: Bearer {accessToken}", проверяет
    через JwtProvider (внутри AuthService) и отдаёт UUID пользователя.
    Любая проблема — 401, тело эндпоинта не выполняется.
    """
    if authorization is None or not authorization.startswith(_BEARER_PREFIX):
        raise _unauthorized("Missing or malformed Authorization header")

    token = authorization[len(_BEARER_PREFIX) :].strip()
    try:
        return await auth_service.get_user_id_from_access_token(token)
    except InvalidTokenError as e:
        raise _unauthorized("Invalid or expired token") from e


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
