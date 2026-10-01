from uuid import UUID
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from tic_tac_toe.domain.exception.auth_exceptions import InvalidTokenError
from tic_tac_toe.domain.service.auth_interface import IAuthService
from tic_tac_toe.infrastructure.database.session import get_db_session

_BEARER_PREFIX = "Bearer "


def get_auth_service(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> IAuthService:
    container = request.app.state.container
    return container.get_auth_service(session)


async def get_current_user_id(
    authorization: str | None = Header(default=None),
    auth_service: IAuthService = Depends(get_auth_service),
) -> UUID:
    """
    UserAuthenticator: Basic-авторизация убрана, вместо неё — Bearer.
    Достаёт accessToken из "Authorization: Bearer {accessToken}", проверяет
    через JwtProvider (внутри AuthService) и отдаёт UUID пользователя.
    Любая проблема — 401, тело эндпоинта не выполняется.
    """
    if authorization is None or not authorization.startswith(_BEARER_PREFIX):
        raise _unauthorized("Missing or malformed Authorization header")

    token = authorization[len(_BEARER_PREFIX):].strip()
    try:
        return await auth_service.get_user_id_from_access_token(token)
    except InvalidTokenError:
        raise _unauthorized("Invalid or expired token")


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
